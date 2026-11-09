"""Rodada 5 (pós-hoc): inventário, recalibração temporal e teste fora da amostra. Plano: reports/diagnostics/calibration/recalibration_out_of_sample/PLANO.md.

Uso (exige TCC_REAL_DATA_AUTHORIZED=YES, levantado pelo proprietário só para esta rodada; somente leitura; saídas agregadas):
    python scripts/analyze_recalibration_out_of_sample.py inventario | calibrar | teste | setout | mensal | componentes | intervalos

`calibrar` mede fator e velocidade, ajusta raio e paciência e grava `calibracao_congelada.json`. As simulações dos períodos de avaliação
(`teste`, `setout`, `mensal`, `componentes`) recusam rodar sem esse arquivo ou se o código mudou depois do congelamento.
Nenhuma saída contém identificadores, coordenadas ou registros individuais: só contagens, quantis e totais.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_robustness_review as r4

from tcc_frota.data.authorization import authorize
from tcc_frota.data.extraction.entities import SEM_PRIME
from tcc_frota.data.extraction.filters import FiltroV1
from tcc_frota.data.time_utils import LOCAL
from tcc_frota.domain.entities import SimParams, reta_km
from tcc_frota.metrics.statistics import moving_block_bootstrap
from tcc_frota.simulation.engine import simulate
from tcc_frota.simulation.historical import DAY_WINDOW_S, PARAMS, build_world

OUT = Path("reports/diagnostics/calibration/recalibration_out_of_sample")
R4 = Path("reports/diagnostics/statistics/robustness_review")
RAIZ = Path("data/raw/v1_viagens")
FREEZE = OUT / "calibracao_congelada.json"
INV_INI, INV_FIM = "2026-01-01", "2026-11-09"  # fim exclusivo
RADIUS_GRID = (2.0, 3.0, 4.0, 4.5, 5.0, 6.0, 8.0)  # mesma grade da calibração de março
PATIENCE_GRID = (60.0, 90.0, 120.0, 180.0, 240.0)
MIN_INSTANTES, MIN_PEDIDOS = 300, 200  # regra (a) de elegibilidade do artigo
WORKERS = 6  # 16 processos esgotaram a memória virtual (arquivo de paginação) em 09/11/2026
# Chave: caminho gravado em `calibracao_congelada.json` (09/11/2026). Valor: caminho atual depois da reestruturação do repositório.
HASHED = {
    "scripts/pos_hoc_rodada5.py": "scripts/analyze_recalibration_out_of_sample.py",
    "scripts/pos_hoc_parecer.py": "scripts/analyze_robustness_review.py",
    "src/tcc_frota/simulation/engine.py": "src/tcc_frota/simulation/engine.py",
    "src/tcc_frota/simulation/historical.py": "src/tcc_frota/simulation/historical.py",
    "src/tcc_frota/assignment/dispatch.py": "src/tcc_frota/assignment/dispatch.py",
    "src/tcc_frota/data/world.py": "src/tcc_frota/data/world.py",
    "src/tcc_frota/data/availability.py": "src/tcc_frota/data/availability.py",
    "src/tcc_frota/data/initial_position.py": "src/tcc_frota/data/initial_position.py",
    "src/tcc_frota/domain/entities.py": "src/tcc_frota/domain/entities.py",
    "reports/pos_hoc_parecer/rodada5/PLANO.md": "reports/diagnostics/calibration/recalibration_out_of_sample/PLANO.md",
}
# Registro das mudanças de caminho e de import feitas depois do congelamento (sem mudança de cálculo), com os diffs conferidos.
EQUIVALENCE = Path("reports/manifests/repository_restructure/frozen_code_equivalence.json")


def _days(a: str, b: str) -> list[str]:
    return [d.strftime("%Y-%m-%d") for d in pd.date_range(a, b)]


CALIB_DAYS = _days("2026-01-01", "2026-08-31")
MONTHS = [f"2026-{m:02d}" for m in range(2, 9)]  # corte mês a mês: m de fevereiro a agosto, calibrado com jan..m-1
TEST = {"26-30/10": _days("2026-10-26", "2026-10-30"), "31/10-08/11": _days("2026-10-31", "2026-11-08")}
TEST_DAYS = TEST["26-30/10"] + TEST["31/10-08/11"]
OLD_PERIODS = r4.PERIODS  # treino, validacao, setembro, outubro
POL4 = {**r4.POL, **r4.POL_D}


# ---------------------------------------------------------------- inventário (item 1)
def _sql_solicitacoes(f: FiltroV1) -> str:
    return (
        "SELECT CAST(DT_REGISTRO AS date) AS dia, COUNT(*) AS solicitacoes, "
        "SUM(CASE WHEN TX_TP_SOLICITACAO = 'TempoReal' THEN 1 ELSE 0 END) AS tempo_real, "
        "SUM(CASE WHEN TX_TP_SOLICITACAO = 'TempoReal' AND TX_STATUS = 'CorridaEncerrada' THEN 1 ELSE 0 END) AS encerradas, "
        "COUNT(DISTINCT CASE WHEN TX_STATUS = 'CorridaEncerrada' THEN CD_MOTORISTA END) AS motoristas_com_corrida_encerrada, "
        "SUM(CASE WHEN NU_DISTANCIA_ACEITE_CHEGUEI > 0 THEN 1 ELSE 0 END) AS com_distancia_aproximacao "
        f"FROM dbo.APP_SOLICITACAO_HIST WHERE CD_REGIAO = ? AND CD_TIPO_SERVICO IN ({f.servicos_sql}) "
        f"AND {SEM_PRIME.format(a='APP_SOLICITACAO_HIST')} AND DT_REGISTRO >= ? AND DT_REGISTRO < ? "
        "GROUP BY CAST(DT_REGISTRO AS date)"
    )


SQL_JORNADAS = (
    "SELECT CAST(DT_INICIO_REALIZADO AS date) AS dia, COUNT(*) AS jornadas_todas_regioes "
    "FROM dbo.APP_JORNADA_MOTORISTA WHERE DT_INICIO_REALIZADO >= ? AND DT_INICIO_REALIZADO < ? "
    "GROUP BY CAST(DT_INICIO_REALIZADO AS date)"
)


def _es_por_dia(leitor, mes: str, f: FiltroV1) -> list[dict]:
    """Instantâneos do registro de ofertas por dia (documentos) e motoristas distintos por dia (cardinalidade aproximada)."""
    idx = f"indexofertamotoristaelasticmodel-{mes}"
    body = {
        "size": 0,
        "query": {"bool": {"filter": [{"term": {"codigoRegiao": f.regiao}}]}},
        "aggs": {
            "d": {
                "date_histogram": {"field": "dataHora", "calendar_interval": "day", "time_zone": "-03:00", "min_doc_count": 1},
                "aggs": {"m": {"cardinality": {"field": "ofertaList.codigo"}}},
            }
        },
    }
    try:
        r = leitor._request("POST", f"/{idx}/_search", body)
    except Exception as exc:  # índice ausente para o mês
        return [{"mes": mes, "erro_es": type(exc).__name__}]
    return [
        {"dia": b["key_as_string"][:10], "instantes_posicao": b["doc_count"], "motoristas_registro_ofertas": b["m"]["value"]}
        for b in r["aggregations"]["d"]["buckets"]
    ]


def cmd_inventario() -> None:
    from tcc_frota.data.reading import ElasticReader, SqlServerReader

    f = FiltroV1()
    with SqlServerReader.from_env("ODS") as r:
        sol = pd.DataFrame(r.query(_sql_solicitacoes(f), (f.regiao, INV_INI, INV_FIM)))
        jor = pd.DataFrame(r.query(SQL_JORNADAS, (INV_INI, INV_FIM)))
    leitor = ElasticReader.from_env(timeout_s=180)
    es_rows = [x for m in [f"2026-{m:02d}" for m in range(1, 12)] for x in _es_por_dia(leitor, m, f)]
    es = pd.DataFrame([x for x in es_rows if "dia" in x])
    # um dia local pode cair em dois índices mensais (fronteira em UTC): soma instantes, máximo de motoristas (aproximação conservadora)
    es = es.groupby("dia", as_index=False).agg(
        instantes_posicao=("instantes_posicao", "sum"), motoristas_registro_ofertas=("motoristas_registro_ofertas", "max")
    )
    erros = [x for x in es_rows if "erro_es" in x]
    for d in (sol, jor):
        d["dia"] = pd.to_datetime(d["dia"]).dt.strftime("%Y-%m-%d")
    df = sol.merge(jor, on="dia", how="outer").merge(es, on="dia", how="outer").sort_values("dia")
    df = df[(df.dia >= INV_INI) & (df.dia < INV_FIM)]
    for ent in ("ods/solicitacao", "ods/jornada_motorista", "ods/veiculo_condutor", "ods/compromissos_externos", "es/posicao_ofertas"):
        df[f"local_{ent.split('/')[1]}"] = df.dia.map(lambda d, e=ent: (RAIZ / e / f"dt={d}" / "part-000.parquet").exists())
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "inventario_por_dia.csv", index=False)
    df["mes"] = df.dia.str[:7]
    num = [c for c in df.columns if df[c].dtype != object and not c.startswith("local_")]
    mes = df.groupby("mes").agg(
        dias_com_solicitacao=("solicitacoes", lambda x: int(x.notna().sum())),
        dias_com_posicao=("instantes_posicao", lambda x: int(x.notna().sum())),
        dias_com_jornada=("jornadas_todas_regioes", lambda x: int(x.notna().sum())),
        **{f"{c}_media_dia": (c, "mean") for c in num},
    )
    mes.round(1).to_csv(OUT / "inventario_por_mes.csv")
    (OUT / "inventario_erros_es.json").write_text(json.dumps(erros, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250)
    print(mes.round(1).to_string())
    print("erros es:", erros)


# ---------------------------------------------------------------- medidas diretas (item 3)
def _ler(fonte: str, ent: str, dia: str, colunas=None) -> pd.DataFrame | None:
    p = RAIZ / fonte / ent / f"dt={dia}" / "part-000.parquet"
    return pd.read_parquet(p, columns=colunas) if p.exists() else None


def _local(ts: pd.Series) -> pd.Series:
    return ts.dt.tz_convert(LOCAL).dt.tz_localize(None)


def _medidas_dia(day: str) -> dict:
    """Aceite, busca, velocidade e fator observados de um dia + linhas do modelo de aceite (ficam em memória; só agregados saem)."""
    sol = _ler("ods", "solicitacao", day)
    st = _ler("ods", "status_solicitacao", day, ["cd_solicitacao", "tx_status", "dt_registro"])
    o = _ler(
        "es", "posicao_ofertas", day, ["cd_motorista", "latitude", "longitude", "event_time", "passageiro_embarcado", "codigo_solicitacao"]
    )
    if sol is None or st is None or o is None:
        return {"dia": day, "faltando": [n for n, x in (("solicitacao", sol), ("status", st), ("posicao", o)) if x is None]}
    d0 = pd.Timestamp(day)
    s = sol.dropna(subset=["dt_registro", "tx_origem_lat", "tx_origem_lng"])
    s = s[(s.dt_registro >= d0) & (s.dt_registro < d0 + pd.Timedelta(days=1)) & (s.tx_tp_solicitacao == "TempoReal")].copy()
    s["cd"] = s.cd_solicitacao.astype("int64")
    st = st[st.tx_status.isin(["CondutorACaminho", "CondutorChegou"])].copy()
    st["cd"] = st.cd_solicitacao.astype("int64")
    first = st.groupby(["cd", "tx_status"]).dt_registro.min().unstack()
    acam = first["CondutorACaminho"] if "CondutorACaminho" in first else pd.Series(dtype="datetime64[ns]")
    cheg = first["CondutorChegou"] if "CondutorChegou" in first else pd.Series(dtype="datetime64[ns]")
    s["acam"] = s.cd.map(acam)
    s["cheg"] = s.cd.map(cheg)
    s["aceito"] = s.acam.notna()
    enc = s[s.tx_status == "CorridaEncerrada"]
    busca = (enc.cheg - enc.dt_registro).dt.total_seconds()
    busca = busca[(busca >= 0) & (busca < 7200)]
    road = enc.nu_distancia_aceite_cheguei.astype(float) / 1000.0
    secs = (enc.cheg - enc.acam).dt.total_seconds()
    ok_v = (secs >= 60) & (road > 0.2)
    vel = (road[ok_v] / (secs[ok_v] / 3600.0)).dropna()
    # fator: última posição do mesmo motorista no registro de ofertas até o aceite (<= 600 s antes)
    o = o.dropna(subset=["cd_motorista", "latitude", "longitude", "event_time"]).copy()
    o["t"] = _local(o.event_time)
    pos = o[["cd_motorista", "t", "latitude", "longitude"]].sort_values("t")
    e = enc[enc.acam.notna() & (road > 0.2)].assign(road=road).sort_values("acam")
    m = pd.merge_asof(
        e[["cd_motorista", "acam", "road", "tx_origem_lat", "tx_origem_lng"]],
        pos,
        left_on="acam",
        right_on="t",
        by="cd_motorista",
        direction="backward",
        tolerance=pd.Timedelta(seconds=600),
    ).dropna(subset=["latitude"])
    reta = np.array([reta_km(a, b, c, d) for a, b, c, d in zip(m.latitude, m.longitude, m.tx_origem_lat, m.tx_origem_lng, strict=True)])
    fator = (m.road.to_numpy() / reta)[reta >= 0.5] if len(m) else np.array([])
    # modelo de aceite: motorista mais próximo no último instantâneo <= registro (<= 300 s), sem passageiro e sem pedido associado (proxy)
    livres = o[~o.passageiro_embarcado.fillna(False).astype(bool) & o.codigo_solicitacao.isna()]
    snaps = np.sort(np.asarray(o.t.drop_duplicates(), dtype="datetime64[ns]"))
    grupos = {np.datetime64(t, "ns"): g for t, g in livres.groupby("t")}
    dist = []
    for t, la, lo in zip(s.dt_registro, s.tx_origem_lat, s.tx_origem_lng, strict=True):
        i = np.searchsorted(snaps, np.datetime64(t), side="right") - 1
        if i < 0 or (np.datetime64(t) - snaps[i]) > np.timedelta64(300, "s") or snaps[i] not in grupos:
            dist.append(np.nan)
            continue
        g = grupos[snaps[i]]
        dist.append(min(reta_km(la, lo, a, b) for a, b in zip(g.latitude, g.longitude, strict=True)))
    return {
        "dia": day,
        "faltando": [],
        "pedidos": int(len(s)),
        "aceitos": int(s.aceito.sum()),
        "instantes_posicao": int(len(snaps)),
        "busca_s": busca.tolist(),
        "vel_kmh": vel.tolist(),
        "fator": fator.tolist(),
        "modelo": list(zip(dist, s.dt_registro.dt.hour.tolist(), s.aceito.astype(int).tolist(), strict=True)),
    }


def _resumo(x) -> dict:
    x = np.asarray(x, float)
    if not len(x):
        return {"n": 0}
    p = np.percentile(x, [10, 25, 50, 75, 90])
    return {"n": int(len(x)), "p10": p[0], "p25": p[1], "mediana": p[2], "p75": p[3], "p90": p[4]}


# ---------------------------------------------------------------- grade de raio e paciência (item 3)
def _elegivel(day: str, reqs) -> tuple[bool, dict]:
    o = _ler("es", "posicao_ofertas", day, ["event_time"])
    inst = int(o.event_time.nunique()) if o is not None else 0
    info = {"dia": day, "pedidos_tempo_real": len(reqs), "instantes_posicao": inst}
    return (inst >= MIN_INSTANTES and len(reqs) >= MIN_PEDIDOS), info


def _world(day: str):
    """Mundo do dia (cenário J). Sem jornada ou vínculo veículo-condutor o cenário J ficaria sem motoristas: é tratado como ausente."""
    falta = [e for e in ("ods/jornada_motorista", "ods/veiculo_condutor") if not (RAIZ / e / f"dt={day}" / "part-000.parquet").exists()]
    if falta:
        return None, f"entidades ausentes para {day}: {falta}"
    try:
        return build_world(day), None
    except FileNotFoundError as exc:
        return None, str(exc)


def _grade_dia(args) -> dict:
    """Para cada (fator, velocidade) pedido, simula A em toda a grade de raio × paciência. Devolve atendidos, pedidos e esperas."""
    day, sets = args
    w, err = _world(day)
    if w is None:
        return {"dia": day, "elegivel": False, "erro": err}
    reqs, drivers, _slim, _orig, co = w
    ok, info = _elegivel(day, reqs)
    out = {**info, "elegivel": ok, "grade": {}}
    if not ok:
        return out
    for key, (f, v) in sets.items():
        for rad in RADIUS_GRID:
            for pat in PATIENCE_GRID:
                p = SimParams(radius_km=rad, speed_kmh=v, road_factor=f, patience_s=pat)
                res = simulate(reqs, drivers, p, DAY_WINDOW_S, {}, commit_origins=co)
                out["grade"][(key, rad, pat)] = (res.served, res.n_requests, np.asarray(res.wait_s, np.float32))
    return out


def _escolher(grid_days: list[dict], key: str, obs_aceite: float, obs_busca: float) -> tuple[dict, list[dict]]:
    rows = []
    for rad in RADIUS_GRID:
        for pat in PATIENCE_GRID:
            sv = n = 0
            ws = []
            for g in grid_days:
                a, b, w = g["grade"][(key, rad, pat)]
                sv, n = sv + a, n + b
                ws.append(w)
            med = float(np.median(np.concatenate(ws))) if ws else float("nan")
            rate = sv / max(n, 1)
            loss = ((rate - obs_aceite) / obs_aceite) ** 2 + ((med - obs_busca) / obs_busca) ** 2
            rows.append(
                {"chave": key, "raio_km": rad, "paciencia_s": pat, "atendimento_sim": rate, "espera_mediana_sim_s": med, "perda": loss}
            )
    best = min(rows, key=lambda r: (r["perda"], r["raio_km"], r["paciencia_s"]))
    return best, rows


def _logit(rows: list[tuple]) -> dict:
    import statsmodels.api as sm

    d = pd.DataFrame(rows, columns=["dist_km", "hora", "aceito"])
    n_total = len(d)
    d = d.dropna()
    out = {"pedidos": n_total, "com_distancia": len(d), "fracao_com_distancia": len(d) / max(n_total, 1)}
    if len(d) < 1000:
        out["nota"] = "dados insuficientes para o modelo"
        return out
    d["faixa"] = pd.cut(d.hora, [-1, 5, 9, 15, 19, 23], labels=["00-05", "06-09", "10-15", "16-19", "20-23"])
    X = pd.get_dummies(d.faixa, prefix="h", drop_first=True, dtype=float)
    X["log_dist"] = np.log(d.dist_km.clip(lower=0.05))
    X = sm.add_constant(X)
    fit = sm.Logit(d.aceito.astype(float), X).fit(disp=False)
    ci = fit.conf_int()
    out["coeficientes"] = {k: {"coef": float(fit.params[k]), "ic95": [float(ci.loc[k, 0]), float(ci.loc[k, 1])]} for k in fit.params.index}
    out["pseudo_r2_mcfadden"] = float(fit.prsquared)
    bins = pd.cut(d.dist_km, [0, 0.5, 1, 2, 3, 4.5, 6, 8, 1e9])
    out["aceite_por_faixa_de_distancia"] = {
        str(k): {"n": int(len(g)), "aceite": float(g.aceito.mean())} for k, g in d.groupby(bins, observed=True)
    }
    return out


def _hashes() -> dict:
    return {chave: hashlib.sha256(Path(p).read_bytes()).hexdigest() for chave, p in HASHED.items()}


def cmd_calibrar() -> None:
    if FREEZE.exists():
        raise SystemExit(f"{FREEZE} já existe: a calibração foi congelada; não recalibrar.")
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        med = list(ex.map(_medidas_dia, CALIB_DAYS))
    faltando = {m["dia"]: m["faltando"] for m in med if m["faltando"]}
    med = [m for m in med if not m["faltando"]]
    # janelas: principal (jan–ago) e corte mês a mês (jan..m-1)
    janelas = {"principal": [m for m in med]}
    for mes in MONTHS:
        janelas[f"ate_{mes}"] = [m for m in med if m["dia"] < f"{mes}-01"]
    medidas = {}
    for k, ms in janelas.items():
        cat = lambda key, ms=ms: [y for m in ms for y in m[key]]
        medidas[k] = {
            "dias_com_medidas": len(ms),
            "fator": _resumo(cat("fator")),
            "velocidade_kmh": _resumo(cat("vel_kmh")),
            "busca_s": _resumo(cat("busca_s")),
            "aceite_obs": sum(m["aceitos"] for m in ms) / max(sum(m["pedidos"] for m in ms), 1),
        }
    sets = {k: (v["fator"]["mediana"], v["velocidade_kmh"]["mediana"]) for k, v in medidas.items()}
    jobs = []
    for day in sorted({m["dia"] for m in med}):
        need = {k: sets[k] for k in sets if k == "principal" or day < f"{k[4:]}-01"}
        jobs.append((day, need))
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        grid = list(ex.map(_grade_dia, jobs))
    eleg = [g for g in grid if g.get("elegivel")]
    nao = [{k: v for k, v in g.items() if k != "grade"} for g in grid if not g.get("elegivel")]
    escolhas, linhas = {}, []
    for k in sets:
        gd = [g for g in eleg if any(kk[0] == k for kk in g["grade"])]
        dias_k = {g["dia"] for g in gd}
        ms = [m for m in janelas[k] if m["dia"] in dias_k]  # observado só nos dias elegíveis simulados
        obs_aceite = sum(m["aceitos"] for m in ms) / max(sum(m["pedidos"] for m in ms), 1)
        obs_busca = float(np.median([y for m in ms for y in m["busca_s"]]))
        best, rows = _escolher(gd, k, obs_aceite, obs_busca)
        linhas += rows
        escolhas[k] = {
            "dias_elegiveis": len(gd),
            "fator": sets[k][0],
            "velocidade_kmh": sets[k][1],
            "raio_km": best["raio_km"],
            "paciencia_s": best["paciencia_s"],
            "aceite_obs": obs_aceite,
            "busca_mediana_obs_s": obs_busca,
            "atendimento_sim": best["atendimento_sim"],
            "espera_mediana_sim_s": best["espera_mediana_sim_s"],
            "perda": best["perda"],
        }
    modelo = _logit([r for m in med for r in m["modelo"]])
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(linhas).to_csv(OUT / "calibracao_grade.csv", index=False)
    congelado = {
        "congelado_em": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "frase": "Setembro, outubro e 26/10–08/11 não foram usados nesta calibração (dias de 01/01 a 31/08/2026).",
        "hashes_sha256": _hashes(),
        "parametros": escolhas,
        "medidas": medidas,
        "dias_sem_entidades": faltando,
        "dias_nao_elegiveis": nao,
        "modelo_de_aceite_descritivo": modelo,
        "duracao_s": round(time.time() - t0, 1),
        "grades": {"raio_km": RADIUS_GRID, "paciencia_s": PATIENCE_GRID},
    }
    FREEZE.write_text(json.dumps(congelado, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(
        json.dumps(
            {k: congelado[k] for k in ("congelado_em", "parametros", "dias_sem_entidades")}, ensure_ascii=False, indent=1, default=float
        )
    )


# ---------------------------------------------------------------- simulações com a calibração congelada (item 4)
def _frozen() -> dict:
    if not FREEZE.exists():
        raise SystemExit("calibração não congelada: rode `calibrar` primeiro.")
    fz = json.loads(FREEZE.read_text(encoding="utf-8"))
    equivalencias = json.loads(EQUIVALENCE.read_text(encoding="utf-8"))["arquivos"] if EQUIVALENCE.exists() else {}

    def aceito(chave: str, atual: str) -> bool:
        congelado = fz["hashes_sha256"].get(chave)
        eq = equivalencias.get(chave, {})
        return atual == congelado or (eq.get("sha256_congelado") == congelado and eq.get("sha256_atual") == atual)

    mudou = [chave for chave, h in _hashes().items() if not aceito(chave, h)]
    if mudou:
        raise SystemExit(f"código ou plano mudou depois do congelamento: {mudou}")
    return fz


def _params(fz: dict, key: str = "principal") -> SimParams:
    e = fz["parametros"][key]
    return SimParams(radius_km=e["raio_km"], speed_kmh=e["velocidade_kmh"], road_factor=e["fator"], patience_s=e["paciencia_s"])


def _sim_job(args) -> list[dict]:
    day, variant, params, pols = args
    w, err = _world(day)
    if w is None:
        return [{"dia": day, "variante": variant, "erro": err}]
    reqs, drivers, _slim, _orig, co = w
    ok, info = _elegivel(day, reqs)
    if not ok:
        return [{"dia": day, "variante": variant, "nao_elegivel": True, **info}]
    return [{"dia": day, "variante": variant, "politica": n, **r4.run_one(reqs, drivers, co, params, b, fn)} for n, (b, fn) in pols.items()]


def _run(jobs) -> tuple[pd.DataFrame, pd.DataFrame]:
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        rows = [r for rs in ex.map(_sim_job, jobs) for r in rs]
    df = pd.DataFrame(rows)
    bad_mask = df.get("politica", pd.Series(index=df.index, dtype=object)).isna()
    return df[~bad_mask].copy(), df[bad_mask].copy()


def _ic_diarios(df: pd.DataFrame, a: str, b: str) -> dict:
    """Diferença média diária (a − b) em km vazio e atendidos: média, IC95% t pareado e bootstrap de blocos de 7 dias."""
    from scipy import stats

    pa = df[df.politica == a].set_index("dia").sort_index()
    pb = df[df.politica == b].set_index("dia").sort_index()
    out = {}
    for col, nome in (("km_vazio", "km"), ("atendidos", "dN")):
        d = (pa[col] - pb[col]).dropna().to_numpy(float)
        n = len(d)
        if n < 2:
            continue
        m, se = d.mean(), d.std(ddof=1) / np.sqrt(n)
        t = stats.t.ppf(0.975, n - 1)
        lo7, hi7 = moving_block_bootstrap(d, block=min(7, n))
        out.update(
            {f"{nome}_media_dia": m, f"{nome}_t_lo": m - t * se, f"{nome}_t_hi": m + t * se, f"{nome}_b7_lo": lo7, f"{nome}_b7_hi": hi7}
        )
    return out


def _sumario(df: pd.DataFrame, keys=("variante", "periodo")) -> pd.DataFrame:
    s = r4.summarize(df, keys)
    extra = []
    for k, g in df.groupby(list(keys)):
        row = dict(zip(keys, k if isinstance(k, tuple) else (k,), strict=True))
        for a, b in (("C", "A"), ("C", "B"), ("D", "C")):
            if {a, b} <= set(g.politica):
                row.update({f"{a}x{b}_{kk}": v for kk, v in _ic_diarios(g, a, b).items()})
        for p, gp in g.groupby("politica"):
            tot = gp.km_vazio.sum() + gp.km_com_passageiro.sum()
            row[f"{p}_km_vazio_sobre_total_pct"] = 100 * gp.km_vazio.sum() / tot
            row[f"{p}_km_total"] = tot
        if {"A", "C"} <= set(g.politica):
            row["CxA_reducao_pp_do_km_total_de_A"] = (
                100 * (g[g.politica == "A"].km_vazio.sum() - g[g.politica == "C"].km_vazio.sum()) / row["A_km_total"]
            )
            row["CxA_queda_participacao_pp"] = row["A_km_vazio_sobre_total_pct"] - row["C_km_vazio_sobre_total_pct"]
        extra.append(row)
    return s.merge(pd.DataFrame(extra), on=list(keys))


def _save(df: pd.DataFrame, bad: pd.DataFrame, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df.drop(columns=[c for c in ("esperas",) if c in df.columns]).to_csv(OUT / f"{name}_por_dia.csv", index=False)
    bad.to_csv(OUT / f"{name}_dias_fora.csv", index=False)


def cmd_teste() -> None:
    fz = _frozen()
    p = _params(fz)
    jobs = [(d, "calibracao_nova", p, POL4) for d in TEST_DAYS] + [(d, "parametros_marco", PARAMS, r4.POL) for d in TEST_DAYS]
    df, bad = _run(jobs)
    per = {d: k for k, ds in TEST.items() for d in ds}
    df["periodo"] = df.dia.map(per)
    tot = df.assign(periodo="26/10-08/11")
    full = pd.concat([df, tot], ignore_index=True)
    _save(df, bad, "teste")
    s = _sumario(full)
    s.to_csv(OUT / "teste_resumo.csv", index=False)
    pd.set_option("display.width", 250)
    print(bad.to_string())
    print(s.T.to_string())


def cmd_setout() -> None:
    fz = _frozen()
    days = OLD_PERIODS["setembro"] + OLD_PERIODS["outubro"]
    df, bad = _run([(d, "calibracao_nova", _params(fz), POL4) for d in days])
    df["periodo"] = df.dia.map(r4._period_of)
    _save(df, bad, "setout")
    s = _sumario(df)
    s.to_csv(OUT / "setout_resumo.csv", index=False)
    print(bad.to_string())
    print(s.T.to_string())


def cmd_mensal() -> None:
    fz = _frozen()
    jobs = []
    for mes in MONTHS:
        p = _params(fz, f"ate_{mes}")
        jobs += [(d, f"mes_{mes}", p, r4.POL) for d in CALIB_DAYS if d.startswith(mes)]
    df, bad = _run(jobs)
    df["periodo"] = df.variante.str[4:]
    _save(df, bad, "mensal")
    s = _sumario(df)
    s.to_csv(OUT / "mensal_resumo.csv", index=False)
    print(s[["variante", "CxA_km_pct", "CxA_dN", "CxA_dN_pp", "CxB_km_pct", "CxB_dN", "A_atend_pct"]].to_string())


def cmd_componentes() -> None:
    """Observado × simulado (A) por período, com os parâmetros de março e com a calibração nova."""
    fz = _frozen()
    periods = {**OLD_PERIODS, **{f"teste_{k}": v for k, v in TEST.items()}}
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        med = {m["dia"]: m for m in ex.map(_medidas_dia, [d for ds in periods.values() for d in ds])}
        comp = {c["dia"]: c for c in ex.map(r4._comp_job, [d for ds in periods.values() for d in ds if not med[d]["faltando"]])}
    jobs = [(d, k, p, {"A": r4.POL["A"]}) for k, p in (("marco", PARAMS), ("nova", _params(fz))) for ds in periods.values() for d in ds]
    sim, bad = _run(jobs)
    rows = []
    for per, ds in periods.items():
        ok = sorted(set(sim.dia) & set(ds))
        ms = [med[d] for d in ok]
        cs = [comp[d] for d in ok if d in comp]
        row = {
            "periodo": per,
            "dias": len(ok),
            "aceite_obs_pct": 100 * sum(m["aceitos"] for m in ms) / max(sum(m["pedidos"] for m in ms), 1),
            "aproximacao_obs_mediana_km": float(np.median([y for c in cs for y in c["pickup_obs_m"]])) / 1000 if cs else np.nan,
            "busca_obs_mediana_s": float(np.median([y for m in ms for y in m["busca_s"]])) if ms else np.nan,
        }
        for k in ("marco", "nova"):
            g = sim[(sim.variante == k) & sim.dia.isin(ok)]
            w = np.concatenate([np.asarray(x) for x in g.esperas]) if len(g) else np.array([])
            row[f"A_{k}_atendidos_pct"] = 100 * g.atendidos.sum() / max(g.pedidos.sum(), 1)
            row[f"A_{k}_aproximacao_media_km"] = g.km_vazio.sum() / max(g.atendidos.sum(), 1)
            row[f"A_{k}_espera_mediana_s"] = float(np.median(w)) if len(w) else np.nan
            row["motoristas_simulados_dia"] = g.motoristas.mean()
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "componentes_antes_depois.csv", index=False)
    pd.set_option("display.width", 250)
    print(out.round(2).T.to_string())


# ---------------------------------------------------------------- faixas e intervalos sobre todas as variantes (item 5)
def cmd_intervalos() -> None:
    _frozen()
    fontes = {
        "base": R4 / "base_por_dia.csv",
        "sens": R4 / "sens_por_dia.csv",
        "disp": R4 / "disp_por_dia.csv",
        "viario": R4 / "viario_por_dia.csv",
        "setout_r5": OUT / "setout_por_dia.csv",
        "teste_r5": OUT / "teste_por_dia.csv",
    }
    rows, atend = [], []
    for fonte, p in fontes.items():
        if not p.exists():
            continue
        df = pd.read_csv(p)
        if "periodo" not in df:
            df["periodo"] = df.dia.map(r4._period_of)
        if fonte == "teste_r5":
            df = pd.concat([df, df.assign(periodo="26/10-08/11")], ignore_index=True)
        for (var, per), g in df.groupby(["variante", "periodo"]):
            if not {"A", "C"} <= set(g.politica):
                continue
            row = {"fonte": fonte, "variante": var, "periodo": per, "dias": g.dia.nunique()}
            for a, b in (("C", "A"), ("C", "B")):
                if {a, b} <= set(g.politica):
                    ka, kb = g[g.politica == a].km_vazio.sum(), g[g.politica == b].km_vazio.sum()
                    row[f"{a}x{b}_km_pct"] = 100 * (ka - kb) / kb
                    row[f"{a}x{b}_dN"] = int(g[g.politica == a].atendidos.sum() - g[g.politica == b].atendidos.sum())
                    row.update({f"{a}x{b}_{k}": v for k, v in _ic_diarios(g, a, b).items()})
            rows.append(row)
            pa = g[g.politica == "A"].set_index("dia")
            pc = g[g.politica == "C"].set_index("dia")
            for d in pa.index.intersection(pc.index):
                atend.append(
                    {
                        "fonte": fonte,
                        "variante": var,
                        "periodo": per,
                        "dia": d,
                        "A_atendidos": pa.loc[d, "atendidos"],
                        "C_atendidos": pc.loc[d, "atendidos"],
                        "pedidos": pa.loc[d, "pedidos"],
                    }
                )
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "intervalos_variantes.csv", index=False)
    pd.DataFrame(atend).to_csv(OUT / "atendimento_por_dia_variantes.csv", index=False)
    cont = (
        out.assign(C_atende_mais=out.CxA_dN > 0, C_atende_menos=out.CxA_dN < 0)
        .groupby("periodo")[["C_atende_mais", "C_atende_menos"]]
        .sum()
    )
    cont.to_csv(OUT / "contagem_variantes_atendimento.csv")
    pd.set_option("display.width", 250)
    print(out.round(2).to_string())
    print(cont.to_string())


if __name__ == "__main__":
    authorize("real")
    {
        "inventario": cmd_inventario,
        "calibrar": cmd_calibrar,
        "teste": cmd_teste,
        "setout": cmd_setout,
        "mensal": cmd_mensal,
        "componentes": cmd_componentes,
        "intervalos": cmd_intervalos,
    }[sys.argv[1]]()
