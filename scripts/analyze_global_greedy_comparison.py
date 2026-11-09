"""Rodada 7 (pós-hoc): conferência dos dados do teste e tabela B, C e D. Plano: docs/REGISTRO_DECISOES.md, R-29 (09/11/2026 17:57).

Uso (exige TCC_REAL_DATA_AUTHORIZED=YES; somente leitura; saídas agregadas):
    python scripts/analyze_global_greedy_comparison.py dados | bcd

`dados` não simula: conta, por dia, registros de posição e pedidos e lê manifestos e o log de lotes.
`bcd` simula B, C e D com parâmetros já fixados (março e a calibração congelada da rodada 5) e confere km e atendidos contra as
execuções anteriores. Nenhuma saída contém identificadores, coordenadas ou registros individuais.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_recalibration_out_of_sample as r5
import analyze_robustness_review as r4

from tcc_frota.data.authorization import authorize
from tcc_frota.simulation.historical import PARAMS

OUT = Path("reports/diagnostics/batching/global_greedy_comparison")
RAIZ = Path("data/raw/v1_viagens")
WORKERS = 6
DIAS = r5._days("2026-09-01", "2026-11-08")
REF_OUT = r5._days("2026-10-01", "2026-10-25")
POL_BCD = {"B": r4.POL["B"], "C": r4.POL["C"], **r4.POL_D}


# ---------------------------------------------------------------- 1. conferência dos dados
def _local(ts: pd.Series) -> pd.Series:
    ts = pd.to_datetime(ts)
    return r5._local(ts) if ts.dt.tz is not None else ts


def _manifesto(fonte: str, ent: str, dia: str) -> dict:
    p = RAIZ / fonte / ent / f"dt={dia}" / "manifest.json"
    if not p.exists():
        return {f"{ent}_manifesto": False}
    m = json.loads(p.read_text(encoding="utf-8"))
    return {
        f"{ent}_manifesto": True,
        f"{ent}_linhas": m.get("linhas"),
        f"{ent}_rejeitadas": m.get("rejeitadas"),
        f"{ent}_gerado_em_utc": m.get("gerado_em_utc"),
    }


def _dia(dia: str) -> tuple[dict, dict]:
    row: dict = {"dia": dia}
    por_hora = {"dia": dia, **dict.fromkeys(range(24), 0)}
    o = r5._ler("es", "posicao_ofertas", dia, ["cd_motorista", "event_time"])
    if o is not None and len(o):
        o = o.dropna(subset=["event_time"]).copy()
        o["t"] = _local(o.event_time)
        o = o[o.t.dt.strftime("%Y-%m-%d") == dia]
        inst_mot = o.dropna(subset=["cd_motorista"]).groupby("cd_motorista").t.nunique()
        row |= {
            "instantes_posicao": int(o.t.nunique()),
            "motoristas_no_registro": int(o.cd_motorista.nunique()),
            "instantes_por_motorista_mediana": float(inst_mot.median()) if len(inst_mot) else np.nan,
            "horas_com_posicao": int(o.t.dt.hour.nunique()),
            "posicao_primeira_hora": float(o.t.min().hour + o.t.min().minute / 60),
            "posicao_ultima_hora": float(o.t.max().hour + o.t.max().minute / 60),
        }
    s = r5._ler("ods", "solicitacao", dia, ["dt_registro", "tx_tp_solicitacao"])
    if s is not None and len(s):
        s = s.dropna(subset=["dt_registro"])
        s = s[(s.dt_registro.dt.strftime("%Y-%m-%d") == dia) & (s.tx_tp_solicitacao == "TempoReal")]
        h = s.dt_registro.dt.hour.value_counts()
        por_hora |= {int(k): int(v) for k, v in h.items()}
        row |= {
            "pedidos_tempo_real": int(len(s)),
            "horas_com_pedido": int(h.size),
            "pedido_primeira_hora": float(s.dt_registro.min().hour + s.dt_registro.min().minute / 60) if len(s) else np.nan,
            "pedido_ultima_hora": float(s.dt_registro.max().hour + s.dt_registro.max().minute / 60) if len(s) else np.nan,
            "hora_media_pedido": float((s.dt_registro.dt.hour + s.dt_registro.dt.minute / 60).mean()) if len(s) else np.nan,
        }
    j = r5._ler("ods", "jornada_motorista", dia)
    row["jornadas"] = int(len(j)) if j is not None else 0
    for fonte, ent in (("es", "posicao_ofertas"), ("ods", "solicitacao"), ("ods", "jornada_motorista"), ("ods", "status_solicitacao")):
        row |= _manifesto(fonte, ent, dia)
    return row, por_hora


def cmd_dados() -> None:
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        res = list(ex.map(_dia, DIAS))
    df = pd.DataFrame([a for a, _ in res])
    ph = pd.DataFrame([b for _, b in res])
    # log de lotes: entradas por (entidade, lote) dos dias conferidos e se alguma traz erro
    log = []
    for linha in (RAIZ / "LOG_LOTES.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            x = json.loads(linha)
        except json.JSONDecodeError:
            continue
        if x.get("lote") in DIAS:
            log.append({"dia": x["lote"], "entidade": x.get("entidade"), "erro": any("erro" in k for k in x), "linhas": x.get("linhas")})
    lg = pd.DataFrame(log)
    if len(lg):
        agg = lg.groupby("dia").agg(lotes_no_log=("entidade", "size"), lotes_com_erro=("erro", "sum"))
        df = df.merge(agg, on="dia", how="left")
    ref = df[df.dia.isin(REF_OUT)]
    lim_inst = 0.5 * ref.instantes_por_motorista_mediana.median()
    df["sinal_a_horas_posicao"] = df.horas_com_posicao < 20
    df["sinal_b_fim_antes_22h"] = (df.pedido_ultima_hora < 22) | (df.posicao_ultima_hora < 22)
    df["sinal_c_instantes_por_motorista"] = df.instantes_por_motorista_mediana < lim_inst
    df["sinal_d_lote"] = df.get("lotes_com_erro", pd.Series(0, index=df.index)).fillna(0) > 0
    for c in ("posicao_ofertas", "solicitacao", "jornada_motorista", "status_solicitacao"):
        df["sinal_d_lote"] |= ~df[f"{c}_manifesto"].fillna(False).astype(bool)
    df["algum_sinal"] = df[[c for c in df.columns if c.startswith("sinal_")]].any(axis=1)
    df["periodo"] = np.select(
        [df.dia < "2026-10-01", df.dia <= "2026-10-25", df.dia <= "2026-10-30"],
        ["setembro", "outubro", "teste_26-30/10"],
        "teste_31/10-08/11",
    )
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "dados_por_dia.csv", index=False)
    ph.to_csv(OUT / "dados_pedidos_por_hora.csv", index=False)
    cols = [
        "instantes_posicao",
        "motoristas_no_registro",
        "instantes_por_motorista_mediana",
        "horas_com_posicao",
        "pedidos_tempo_real",
        "horas_com_pedido",
        "hora_media_pedido",
        "jornadas",
    ]
    resumo = df.groupby("periodo")[cols].median().round(2)
    resumo["dias"] = df.groupby("periodo").size()
    resumo["dias_com_sinal"] = df.groupby("periodo").algum_sinal.sum()
    resumo.to_csv(OUT / "dados_resumo_periodo.csv")
    # distribuição horária (fração dos pedidos por faixa) por período
    ph["periodo"] = df.periodo.values
    faixa = ph.groupby("periodo")[list(range(24))].sum()
    faixa = faixa.div(faixa.sum(axis=1), axis=0)
    blocos = {"00-05": range(0, 6), "06-11": range(6, 12), "12-17": range(12, 18), "18-23": range(18, 24)}
    dist = pd.DataFrame({k: faixa[list(v)].sum(axis=1) for k, v in blocos.items()}).round(3)
    dist.to_csv(OUT / "dados_distribuicao_horaria.csv")
    pd.set_option("display.width", 250)
    print("limite instantes por motorista (metade da mediana de 01-25/10):", lim_inst)
    print(resumo.to_string())
    print(dist.to_string())
    print(df[df.dia >= "2026-10-26"][["dia", *cols, "pedido_ultima_hora", "posicao_ultima_hora", "algum_sinal"]].to_string())


# ---------------------------------------------------------------- 2. tabela B, C e D
def _job_marco(day: str) -> list[dict]:
    reqs, drivers, _slim, _orig, co = r4.load_world(day)
    return [
        {"dia": day, "calibracao": "marco", "politica": n, **r4.run_one(reqs, drivers, co, PARAMS, b, fn)} for n, (b, fn) in POL_BCD.items()
    ]


def _job_nova(args) -> list[dict]:
    day, params = args
    rows = r5._sim_job((day, "calibracao_nova", params, POL_BCD))
    for r in rows:
        r["calibracao"] = "nova"
    return rows


def _periodo(d: str) -> str:
    return "setembro" if d < "2026-10-01" else ("outubro" if d <= "2026-10-25" else "teste_26/10-08/11")


def cmd_bcd() -> None:
    fz = r5._frozen()  # recusa se o código ou o plano da rodada 5 mudaram depois do congelamento
    p_nova = r5._params(fz)
    setout = r4.PERIODS["setembro"] + r4.PERIODS["outubro"]
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        rows = [r for rs in ex.map(_job_marco, setout) for r in rs]
        rows += [r for rs in ex.map(_job_nova, [(d, p_nova) for d in setout + r5.TEST_DAYS]) for r in rs]
    df = pd.DataFrame(rows)
    df = df[df.politica.notna()].copy()
    df["periodo"] = df.dia.map(_periodo)
    # conferência contra as execuções anteriores (km e atendidos por dia e política)
    ant = pd.concat(
        [
            pd.read_csv("reports/diagnostics/statistics/robustness_review/base_por_dia.csv").assign(calibracao="marco"),
            pd.read_csv("reports/diagnostics/calibration/recalibration_out_of_sample/setout_por_dia.csv").assign(calibracao="nova"),
            pd.read_csv("reports/diagnostics/calibration/recalibration_out_of_sample/teste_por_dia.csv")
            .query("variante == 'calibracao_nova'")
            .assign(calibracao="nova"),
        ]
    )
    m = df.merge(
        ant[["dia", "calibracao", "politica", "km_vazio", "atendidos"]], on=["dia", "calibracao", "politica"], suffixes=("", "_ant")
    )
    conf = {
        "pares_conferidos": int(len(m)),
        "pares_simulados": int(len(df)),
        "max_dif_km": float((m.km_vazio - m.km_vazio_ant).abs().max()),
        "atendidos_diferentes": int((m.atendidos != m.atendidos_ant).sum()),
    }
    out = []
    for (cal, per, pol), g in df.groupby(["calibracao", "periodo", "politica"]):
        w = np.concatenate([np.asarray(x) for x in g.esperas])
        out.append(
            {
                "calibracao": cal,
                "periodo": per,
                "politica": pol,
                "dias": int(g.dia.nunique()),
                "pedidos": int(g.pedidos.sum()),
                "atendidos": int(g.atendidos.sum()),
                "km_vazio": float(g.km_vazio.sum()),
                "km_por_atendido": float(g.km_vazio.sum() / g.atendidos.sum()),
                "espera_media_s": float(w.mean()),
                "espera_p90_s": float(np.percentile(w, 90)),
            }
        )
    tab = pd.DataFrame(out)
    OUT.mkdir(parents=True, exist_ok=True)
    tab.to_csv(OUT / "bcd_resumo.csv", index=False)
    df.drop(columns=["esperas"]).to_csv(OUT / "bcd_por_dia.csv", index=False)
    (OUT / "bcd_conferencia.json").write_text(json.dumps(conf, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250)
    print(json.dumps(conf))
    print(tab.round(2).to_string())


# ---------------------------------------------------------------- 1b. adendo: pedidos por região e serviço (só contagens)
SQL_SERVICOS = (
    "SELECT CAST(DT_REGISTRO AS date) AS dia, CD_REGIAO AS regiao, CD_TIPO_SERVICO AS servico, "
    "CASE WHEN TX_MODELO_SOLICITACAO = 'Prime' THEN 1 ELSE 0 END AS prime, COUNT(*) AS pedidos_tempo_real "
    "FROM dbo.APP_SOLICITACAO_HIST WHERE TX_TP_SOLICITACAO = 'TempoReal' AND DT_REGISTRO >= ? AND DT_REGISTRO < ? "
    "GROUP BY CAST(DT_REGISTRO AS date), CD_REGIAO, CD_TIPO_SERVICO, CASE WHEN TX_MODELO_SOLICITACAO = 'Prime' THEN 1 ELSE 0 END"
)


def cmd_servicos() -> None:
    from tcc_frota.data.reading import SqlServerReader

    with SqlServerReader.from_env("ODS") as r:
        df = pd.DataFrame(r.query(SQL_SERVICOS, ("2026-10-19", "2026-11-09")))
    df["dia"] = pd.to_datetime(df["dia"]).dt.strftime("%Y-%m-%d")
    df["no_filtro"] = (df.regiao == 1) & df.servico.isin([1, 11, 12, 19]) & (df.prime == 0)
    df["grupo"] = np.where(df.no_filtro, "no_filtro", np.where(df.regiao == 1, "regiao1_fora_do_filtro", "outras_regioes"))
    tab = df.pivot_table(index="dia", columns="grupo", values="pedidos_tempo_real", aggfunc="sum", fill_value=0)
    serv = df[df.regiao == 1].pivot_table(index="dia", columns="servico", values="pedidos_tempo_real", aggfunc="sum", fill_value=0)
    OUT.mkdir(parents=True, exist_ok=True)
    tab.to_csv(OUT / "dados_pedidos_por_grupo.csv")
    serv.to_csv(OUT / "dados_pedidos_regiao1_por_servico.csv")
    pd.set_option("display.width", 250)
    print(tab.to_string())
    print(serv.to_string())


if __name__ == "__main__":
    authorize("real")
    {"dados": cmd_dados, "servicos": cmd_servicos, "bcd": cmd_bcd}[sys.argv[1]]()
