"""Análises PÓS-HOC do parecer (plano em reports/diagnostics/statistics/robustness_review/PLANO.md). Não alteram o experimento congelado.

Uso (exige TCC_REAL_DATA_AUTHORIZED=YES, levantado pelo proprietário; só processamento local; saídas agregadas):
    python scripts/analyze_robustness_review.py base|sens|disp|janelas|componentes

Os mundos dos dias reais vêm do cache da execução congelada (hash do código do mundo d5cb1289caea, registrado no manifesto congelado).
Nenhuma saída contém identificadores, coordenadas ou registros individuais.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from tcc_frota.assignment import dispatch as dp
from tcc_frota.data.authorization import authorize
from tcc_frota.domain.entities import reta_km
from tcc_frota.simulation.engine import simulate
from tcc_frota.simulation.historical import DAY_WINDOW_S, PARAMS

OUT = Path("reports/diagnostics/statistics/robustness_review")
CACHE = Path("data/processed/world_cache")
RAIZ = Path("data/raw/v1_viagens")
FROZEN_WORLD_HASH = "d5cb1289caea"
FROZEN = Path("reports/historical/frozen_evaluation/execucao/grupo_B")


def _days(a: str, b: str) -> list[str]:
    return [d.strftime("%Y-%m-%d") for d in pd.date_range(a, b)]


PERIODS = {
    "treino": _days("2026-02-01", "2026-03-15"),
    "validacao": _days("2026-03-16", "2026-03-31"),
    "setembro": _days("2026-09-16", "2026-09-30"),
    "outubro": _days("2026-10-01", "2026-10-25"),
}
POL = {"A": (None, None), "B": (60.0, dp.POLICIES["nearest_fifo"]), "C": (60.0, dp.POLICIES["hungarian"])}
POL_D = {"D": (60.0, dp.POST_HOC_POLICIES["global_greedy"])}


class _FrozenUnpickler(pickle.Unpickler):
    """Os pickles congelados referem as classes pelo nome do pacote antigo; são as mesmas classes, hoje em `domain.entities`."""

    def find_class(self, module, name):
        # nome do módulo gravado no pickle (não é import de código removido): pacote antigo `v2` -> `domain.entities`
        if module.split(".")[:2] == ["tcc_frota", "v2"]:
            module = "tcc_frota.domain.entities"
        return super().find_class(module, name)


def load_world(day: str):
    import io

    return _FrozenUnpickler(io.BytesIO((CACHE / f"mundo_{day}_{FROZEN_WORLD_HASH}.pkl").read_bytes())).load()


class Spy:
    """Envolve a política de lote e conta, por pedido, os lotes em que ele tinha veículo elegível e não recebeu par."""

    def __init__(self, fn):
        self.fn, self.preterido = fn, {}

    def __call__(self, t, pend, cands):
        pares = self.fn(t, pend, cands)
        got = {r for r, _ in pares}
        for rid in cands:
            if rid not in got:
                self.preterido[rid] = self.preterido.get(rid, 0) + 1
        return pares


def run_one(reqs, drivers, commit_origins, params, batch, fn) -> dict:
    spy = Spy(fn) if fn else None
    res = simulate(reqs, drivers, params, DAY_WINDOW_S, {}, commit_origins=commit_origins, batch_s=batch, assigner=spy)
    served = res.served_ids
    trip = sum(reta_km(r.lat, r.lon, r.dlat, r.dlon) * params.road_factor for r in reqs if r.rid in served)
    out = {
        "pedidos": res.n_requests,
        "atendidos": res.served,
        "expirados": res.n_requests - res.served,
        "km_vazio": res.empty_km,
        "km_com_passageiro": trip,
        "esperas": list(map(float, res.wait_s)),
        "motoristas": len(drivers),
    }
    if spy:
        pret = spy.preterido
        out["preteridos_e_expirados"] = sum(1 for rid in pret if rid not in served)
        out["preteridos_e_atendidos"] = sum(1 for rid in pret if rid in served)
        out["lotes_preterido_total"] = int(sum(pret.values()))
        out["lotes_preterido_max"] = int(max(pret.values(), default=0))
    return out


def _day_job(args):
    day, variant, params, pols, drop = args
    reqs, drivers, _slim, _orig, co = load_world(day)
    if drop:
        drivers = [d for d in drivers if int(hashlib.sha256(d.did.encode()).hexdigest(), 16) % 5 != 0]
        keep = {d.did for d in drivers}
        co = {k: v for k, v in co.items() if k in keep}
    rows = []
    for name, (batch, fn) in pols.items():
        r = run_one(reqs, drivers, co, params, batch, fn)
        rows.append({"dia": day, "variante": variant, "politica": name, **r})
    return rows


def _run(jobs) -> pd.DataFrame:
    with ProcessPoolExecutor() as ex:
        rows = [r for rs in ex.map(_day_job, jobs) for r in rs]
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame, keys=("variante", "periodo")) -> pd.DataFrame:
    """Totais por (variante, período, política) e contrastes C×A, C×B, D×C (km em %, atendidos em contagem e p.p.)."""
    out = []
    for k, g in df.groupby(list(keys)):
        tot = {}
        for p, gp in g.groupby("politica"):
            w = np.concatenate([np.asarray(x) for x in gp.esperas]) if len(gp) else np.array([])
            tot[p] = {
                "pedidos": int(gp.pedidos.sum()),
                "atendidos": int(gp.atendidos.sum()),
                "km_vazio": float(gp.km_vazio.sum()),
                "km_com_passageiro": float(gp.km_com_passageiro.sum()),
                "p90": float(np.percentile(w, 90)) if len(w) else np.nan,
                "dias": int(gp.dia.nunique()),
            }
        row = dict(zip(keys, k if isinstance(k, tuple) else (k,), strict=True))
        for a, b in (("C", "A"), ("C", "B"), ("B", "A"), ("D", "C"), ("D", "A")):
            if a in tot and b in tot:
                ta, tb = tot[a], tot[b]
                da = g[g.politica == a].set_index("dia")
                db = g[g.politica == b].set_index("dia")
                dd = (da.km_vazio - db.km_vazio).dropna()
                row[f"{a}x{b}_km_pct"] = 100 * (ta["km_vazio"] - tb["km_vazio"]) / tb["km_vazio"]
                row[f"{a}x{b}_dN"] = ta["atendidos"] - tb["atendidos"]
                row[f"{a}x{b}_dN_pp"] = 100 * (ta["atendidos"] - tb["atendidos"]) / ta["pedidos"]
                row[f"{a}x{b}_dias_melhor_pior"] = f"{int((dd < 0).sum())}/{int((dd > 0).sum())}"
                row[f"{a}x{b}_p90_dif_s"] = ta["p90"] - tb["p90"]
        for p, t in tot.items():
            row[f"{p}_atend_pct"] = 100 * t["atendidos"] / t["pedidos"]
            row[f"{p}_km_vazio"] = t["km_vazio"]
        out.append(row)
    return pd.DataFrame(out)


def _save(df: pd.DataFrame, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df.drop(columns=[c for c in ("esperas",) if c in df.columns]).to_csv(OUT / f"{name}_por_dia.csv", index=False)


def _period_of(day: str) -> str:
    return next(p for p, ds in PERIODS.items() if day in ds)


# ---------------------------------------------------------------- base (P5 D×C e P7)
def cmd_base() -> None:
    days = PERIODS["setembro"] + PERIODS["outubro"]
    df = _run([(d, "base", PARAMS, {**POL, **POL_D}, False) for d in days])
    df["periodo"] = df.dia.map(_period_of)
    # conferência com o congelado
    diffs = []
    for d in days:
        fz = pd.read_parquet(FROZEN / ("replicacao" if d < "2026-10-01" else "final") / f"dia={d}.parquet")
        for pol, cfg in (("A", "B0_imediato_atual"), ("B", "B_lote60s_guloso_fifo"), ("C", "B_lote60s_hungaro")):
            f = fz[fz.config == cfg].iloc[0]
            n = df[(df.dia == d) & (df.politica == pol)].iloc[0]
            diffs.append((abs(f.km_vazio_total - n.km_vazio), int(f.atendidos != n.atendidos)))
    conf = {"pares_dia_politica": len(diffs), "max_dif_km": max(x for x, _ in diffs), "atendidos_diferentes": sum(y for _, y in diffs)}
    _save(df, "base")
    s = summarize(df)
    s.to_csv(OUT / "base_resumo.csv", index=False)
    # espera e prática
    pr = []
    for (per, pol), g in df.groupby(["periodo", "politica"]):
        w = np.concatenate([np.asarray(x) for x in g.esperas])
        row = {
            "periodo": per,
            "politica": pol,
            "dias": g.dia.nunique(),
            "pedidos": int(g.pedidos.sum()),
            "atendidos": int(g.atendidos.sum()),
            "expirados": int(g.expirados.sum()),
            "km_vazio": float(g.km_vazio.sum()),
            "km_com_passageiro": float(g.km_com_passageiro.sum()),
            "km_vazio_sobre_total_modelado_pct": float(100 * g.km_vazio.sum() / (g.km_vazio.sum() + g.km_com_passageiro.sum())),
            "km_viagem_medio": float(g.km_com_passageiro.sum() / g.atendidos.sum()),
            "km_vazio_por_dia": float(g.km_vazio.sum() / g.dia.nunique()),
            "espera_p50_s": float(np.percentile(w, 50)),
            "espera_p90_s": float(np.percentile(w, 90)),
            "espera_p95_s": float(np.percentile(w, 95)),
            "espera_p99_s": float(np.percentile(w, 99)),
            "espera_max_s": float(w.max()),
        }
        for c in ("preteridos_e_expirados", "preteridos_e_atendidos", "lotes_preterido_total"):
            if c in g and g[c].notna().any():
                row[c] = int(g[c].sum())
        if "lotes_preterido_max" in g and g["lotes_preterido_max"].notna().any():
            row["lotes_preterido_max"] = int(g["lotes_preterido_max"].max())
        pr.append(row)
    pd.DataFrame(pr).to_csv(OUT / "base_pratica_e_justica.csv", index=False)
    (OUT / "base_conferencia_congelado.json").write_text(json.dumps(conf, indent=1), encoding="utf-8")
    print(json.dumps(conf), "\n", s.T.to_string(), "\n", pd.DataFrame(pr).T.to_string())


# ---------------------------------------------------------------- sensibilidade de parâmetros (P3)
def cmd_sens() -> None:
    days = PERIODS["setembro"] + PERIODS["outubro"]
    variants = {
        "fator_1.2": replace(PARAMS, road_factor=1.2),
        "fator_1.6": replace(PARAMS, road_factor=1.6),
        "velocidade_-25%": replace(PARAMS, speed_kmh=PARAMS.speed_kmh * 0.75),
        "velocidade_+25%": replace(PARAMS, speed_kmh=PARAMS.speed_kmh * 1.25),
        "raio_3.5km": replace(PARAMS, radius_km=3.5),
        "raio_5.5km": replace(PARAMS, radius_km=5.5),
        "paciencia_120s": replace(PARAMS, patience_s=120.0),
        "paciencia_300s": replace(PARAMS, patience_s=300.0),
    }
    df = _run([(d, v, p, POL, False) for v, p in variants.items() for d in days])
    df["periodo"] = df.dia.map(_period_of)
    _save(df, "sens")
    s = summarize(df)
    s.to_csv(OUT / "sens_resumo.csv", index=False)
    print(s[["variante", "periodo", "CxA_km_pct", "CxA_dN", "CxA_dN_pp", "CxB_km_pct", "CxB_dN", "A_atend_pct"]].to_string())


# ---------------------------------------------------------------- disponibilidade (P2)
def _rebuild_job(args):
    day, cenario, gap = args
    from tcc_frota.data.world import montar, origens_por_motorista

    reqs, drivers, rel, orig = montar(RAIZ, day, cenario=cenario, gap_ponte_s=gap)
    co = origens_por_motorista(drivers, orig)
    rows = []
    for name, (batch, fn) in POL.items():
        r = run_one(reqs, drivers, co, PARAMS, batch, fn)
        rows.append({"dia": day, "variante": f"{cenario}_ponte{int(gap)}", "politica": name, **r})
    jr = rel.get("jornada_registrada", {})
    info = {
        "dia": day,
        "variante": f"{cenario}_ponte{int(gap)}",
        "motoristas_no_registro_de_ofertas": rel.get("motoristas_online_es"),
        "motoristas_simulados": rel.get("motoristas_simulados"),
        **{f"jornadas_{k}": v for k, v in jr.items() if isinstance(v, (int, float, bool)) and k != "disponivel"},
    }
    return rows, info


def cmd_disp() -> None:
    days = PERIODS["setembro"] + PERIODS["outubro"]
    jobs = [(d, "J", 1200.0) for d in days] + [(d, "J", 600.0) for d in days] + [(d, "J", 2400.0) for d in days]
    jobs += [(d, "E", 1200.0) for d in days]
    with ProcessPoolExecutor() as ex:
        res = list(ex.map(_rebuild_job, jobs))
    df = pd.DataFrame([r for rows, _ in res for r in rows])
    info = pd.DataFrame([i for _, i in res])
    red = _run([(d, "J_reducao20", PARAMS, POL, True) for d in days])
    df = pd.concat([df, red], ignore_index=True)
    df["periodo"] = df.dia.map(_period_of)
    _save(df, "disp")
    info.to_csv(OUT / "disp_contagens_por_dia.csv", index=False)
    s = summarize(df)
    s.to_csv(OUT / "disp_resumo.csv", index=False)
    mot = df[df.politica == "A"].groupby(["variante", "periodo"]).motoristas.mean().round(1)
    print(s[["variante", "periodo", "CxA_km_pct", "CxA_dN", "CxA_dN_pp", "CxB_km_pct", "CxB_dN", "A_atend_pct"]].to_string())
    print(mot.to_string())


def cmd_contagens() -> None:
    """Contagens de disponibilidade por dia em todos os períodos (reconstrução J padrão, sem simular)."""
    days = [d for ds in PERIODS.values() for d in ds]
    with ProcessPoolExecutor() as ex:
        res = list(ex.map(_count_job, days))
    df = pd.DataFrame(res)
    df["periodo"] = df.dia.map(_period_of)
    df.to_csv(OUT / "disp_contagens_todos_periodos.csv", index=False)
    print(df.groupby("periodo").mean(numeric_only=True).round(1).T.to_string())


def _count_job(day):
    from tcc_frota.data.world import montar

    _reqs, _drivers, rel, _orig = montar(RAIZ, day, cenario="J")
    jr = rel.get("jornada_registrada", {})
    s = pd.read_parquet(
        RAIZ / "ods" / "solicitacao" / f"dt={day}" / "part-000.parquet", columns=["tx_tp_solicitacao", "tx_status", "cd_motorista"]
    )
    s = s[s.tx_tp_solicitacao == "TempoReal"]
    return {
        "dia": day,
        "pedidos_tempo_real": len(s),
        "motoristas_com_corrida_encerrada": int(s[s.tx_status == "CorridaEncerrada"].cd_motorista.nunique()),
        "motoristas_no_registro_de_ofertas": rel.get("motoristas_online_es"),
        "motoristas_simulados": rel.get("motoristas_simulados"),
        **{f"jornadas_{k}": v for k, v in jr.items() if isinstance(v, (int, float)) and not isinstance(v, bool)},
    }


# ---------------------------------------------------------------- janelas no treino (P5)
def cmd_janelas() -> None:
    days = PERIODS["treino"]
    jobs = [(d, "A", PARAMS, {"A": POL["A"]}, False) for d in days]
    for w in (30.0, 60.0, 120.0):
        pols = {
            "B": (w, dp.POLICIES["nearest_fifo"]),
            "C": (w, dp.POLICIES["hungarian"]),
            "D": (w, dp.POST_HOC_POLICIES["global_greedy"]),
        }
        jobs += [(d, f"janela_{int(w)}s", PARAMS, pols, False) for d in days]
    df = _run(jobs)
    a = df[df.variante == "A"]
    df = pd.concat(
        [df[df.variante != "A"]] + [a.assign(variante=v) for v in ("janela_30s", "janela_60s", "janela_120s")], ignore_index=True
    )
    df["periodo"] = "treino"
    _save(df, "janelas_treino")
    s = summarize(df)
    s.to_csv(OUT / "janelas_treino_resumo.csv", index=False)
    cols = ["variante", "CxA_km_pct", "CxA_dN", "CxA_p90_dif_s", "CxB_km_pct", "CxB_dN", "DxC_km_pct", "DxC_dN", "DxA_km_pct", "DxA_dN"]
    print(s[cols].to_string())


# ---------------------------------------------------------------- componentes observados (P1)
def _comp_job(day):
    s = pd.read_parquet(RAIZ / "ods" / "solicitacao" / f"dt={day}" / "part-000.parquet")
    s = s[s.tx_tp_solicitacao == "TempoReal"]
    enc = s[s.tx_status == "CorridaEncerrada"]
    pick = enc.nu_distancia_aceite_cheguei
    espera = (enc.dt_inicio_realizada - enc.dt_registro).dt.total_seconds()
    dur = (enc.dt_fim_realizada - enc.dt_inicio_realizada).dt.total_seconds()
    o = pd.read_parquet(
        RAIZ / "es" / "posicao_ofertas" / f"dt={day}" / "part-000.parquet",
        columns=["codigo_solicitacao", "passageiro_embarcado", "latitude", "longitude", "distancia_restante", "event_time"],
    )
    o = o[o.codigo_solicitacao.notna() & (o.passageiro_embarcado == False) & o.distancia_restante.notna()]  # noqa: E712
    orig = s.set_index(s.cd_solicitacao.astype("int64"))[["tx_origem_lat", "tx_origem_lng"]]
    o = o.assign(cod=pd.to_numeric(o.codigo_solicitacao, errors="coerce")).dropna(subset=["cod"])
    o = o.assign(cod=o.cod.astype("int64")).merge(orig, left_on="cod", right_index=True)
    reta = np.array([reta_km(a, b, c, d) for a, b, c, d in zip(o.latitude, o.longitude, o.tx_origem_lat, o.tx_origem_lng, strict=True)])
    o = o.assign(reta=reta, rest_km=o.distancia_restante / 1000.0)
    ok = o[(o.reta >= 0.3)]
    ratio = ok.rest_km / ok.reta
    ratio = ratio[(ratio >= 0.8) & (ratio <= 5)]
    o = o.sort_values(["cod", "event_time"])
    dt = o.groupby("cod").event_time.diff().dt.total_seconds()
    dd = -o.groupby("cod").rest_km.diff()
    v = (dd / (dt / 3600.0))[(dt >= 60) & (dt <= 300)]
    v = v[(v > 0) & (v <= 120)]
    return {
        "dia": day,
        "pedidos": len(s),
        "status": s.tx_status.value_counts().to_dict(),
        "pickup_obs_m": pick[pick.notna() & (pick > 0)].tolist(),
        "pickup_nulo_ou_zero": int((pick.isna() | (pick <= 0)).sum()),
        "espera_obs_s": espera[(espera >= 0) & (espera < 7200)].tolist(),
        "duracao_obs_s": dur[(dur > 0) & (dur < 4 * 3600)].tolist(),
        "fator_obs": ratio.tolist(),
        "vel_obs": v.tolist(),
    }


def _q(x) -> dict:
    x = np.asarray(x, float)
    if not len(x):
        return {"n": 0}
    lo, hi = np.percentile(x, [5, 95])
    xt = x[(x >= lo) & (x <= hi)]
    return {
        "n": int(len(x)),
        "p25": float(np.percentile(x, 25)),
        "mediana": float(np.median(x)),
        "p75": float(np.percentile(x, 75)),
        "media_aparada_5pct": float(xt.mean()),
    }


def cmd_componentes() -> None:
    with ProcessPoolExecutor() as ex:
        res = list(ex.map(_comp_job, [d for ds in PERIODS.values() for d in ds]))
    out = {}
    for per, ds in PERIODS.items():
        rs = [r for r in res if r["dia"] in ds]
        st: dict = {}
        for r in rs:
            for k, v in r["status"].items():
                st[k] = st.get(k, 0) + v
        n = sum(r["pedidos"] for r in rs)
        cat = lambda xs: [y for r in rs for y in r[xs]]
        out[per] = {
            "dias": len(rs),
            "pedidos": n,
            "status_pct": {k: round(100 * v / n, 2) for k, v in sorted(st.items(), key=lambda x: -x[1])},
            "corrida_encerrada_pct": round(100 * st.get("CorridaEncerrada", 0) / n, 2),
            "aceitas_pct (encerrada + canceladas pos-aceite)": round(
                100 * sum(v for k, v in st.items() if k == "CorridaEncerrada" or "PosAceite" in k) / n, 2
            ),
            "pickup_observado_km": {k: (v / 1000 if k != "n" else v) for k, v in _q(cat("pickup_obs_m")).items()},
            "pickup_observado_nulo_ou_zero": sum(r["pickup_nulo_ou_zero"] for r in rs),
            "espera_observada_registro_ate_inicio_s": _q(cat("espera_obs_s")),
            "duracao_viagem_observada_s": _q(cat("duracao_obs_s")),
            "fator_rua_reta_registro_ofertas": _q(cat("fator_obs")),
            "velocidade_aproximacao_registro_ofertas_kmh": _q(cat("vel_obs")),
        }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "componentes_observados.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


def cmd_simulado_a() -> None:
    """P1: grandezas simuladas de A em cada período, para pôr ao lado das observadas."""
    rows = []
    for per, ds in PERIODS.items():
        df = _run([(d, per, PARAMS, {"A": POL["A"]}, False) for d in ds])
        w = np.concatenate([np.asarray(x) for x in df.esperas])
        rows.append(
            {
                "periodo": per,
                "pedidos": int(df.pedidos.sum()),
                "atendidos_A_pct": 100 * df.atendidos.sum() / df.pedidos.sum(),
                "km_aproximacao_por_atendido_A": df.km_vazio.sum() / df.atendidos.sum(),
                "espera_mediana_A_s": float(np.median(w)),
                "motoristas_por_dia": df.motoristas.mean(),
            }
        )
    o = pd.DataFrame(rows)
    o.to_csv(OUT / "componentes_simulado_A.csv", index=False)
    print(o.round(2).to_string())


# ---------------------------------------------------------------- distância viária em subconjunto (P3)
VIARIO_DIAS = ("2026-10-01", "2026-10-08", "2026-10-15", "2026-10-22")  # fixados por calendário no plano
SNAP_LIMITE_KM = 0.5


class MetricaViariaReal:
    """km pela rede OSM (Dijkstra dirigido) entre coordenadas reais: liga cada ponto ao nó mais próximo (trecho de ligação em linha reta,
    somado) e guarda as distâncias por nó de origem (LRU). Mesma métrica para todas as políticas."""

    def __init__(self, maxsize: int = 400):
        from collections import OrderedDict

        from scipy.spatial import cKDTree

        from tcc_frota.scenarios.geography import construir_rede

        r = construir_rede()
        self.g, self.lat, self.lon = r.grafo, r.lat, r.lon
        self.k = np.cos(np.radians(-20.3))
        self.tree = cKDTree(np.c_[self.lat, self.lon * self.k])
        self.cache: OrderedDict = OrderedDict()
        self.snap: dict = {}
        self.maxsize = maxsize
        self.snap_longe = 0
        self.snap_total = 0

    def _no(self, lat, lon):
        key = (lat, lon)
        v = self.snap.get(key)
        if v is None:
            _, i = self.tree.query((lat, lon * self.k))
            d = reta_km(lat, lon, self.lat[i], self.lon[i])
            v = (int(i), d)
            self.snap[key] = v
            self.snap_total += 1
            self.snap_longe += int(d > SNAP_LIMITE_KM)
        return v

    def km(self, lat1, lon1, lat2, lon2):
        from scipy.sparse.csgraph import dijkstra

        a, da = self._no(lat1, lon1)
        b, db = self._no(lat2, lon2)
        row = self.cache.get(a)
        if row is None:
            row = dijkstra(self.g, indices=a).astype(np.float32) / 1000.0
            self.cache[a] = row
            if len(self.cache) > self.maxsize:
                self.cache.popitem(last=False)
        else:
            self.cache.move_to_end(a)
        return da + float(row[b]) + db


def _viario_job(day):
    reqs, drivers, _slim, _orig, co = load_world(day)
    met = MetricaViariaReal()
    params = replace(PARAMS, radius_km=PARAMS.radius_km * PARAMS.road_factor)  # raio por via equivalente (4,5 × 1,3012 km)
    rows = []
    for name, (batch, fn) in POL.items():
        res = simulate(reqs, drivers, params, DAY_WINDOW_S, {}, commit_origins=co, batch_s=batch, assigner=fn, metric=met)
        rows.append(
            {
                "dia": day,
                "variante": "viario_osm",
                "politica": name,
                "pedidos": res.n_requests,
                "atendidos": res.served,
                "expirados": res.n_requests - res.served,
                "km_vazio": res.empty_km,
                "km_com_passageiro": 0.0,
                "esperas": list(map(float, res.wait_s)),
                "motoristas": len(drivers),
                "pontos_ligados": met.snap_total,
                "pontos_a_mais_de_500m_da_rede": met.snap_longe,
            }
        )
    return rows


def cmd_viario() -> None:
    with ProcessPoolExecutor(max_workers=4) as ex:
        df = pd.DataFrame([r for rs in ex.map(_viario_job, VIARIO_DIAS) for r in rs])
    base = pd.read_csv(OUT / "base_por_dia.csv")
    base = base[base.dia.isin(VIARIO_DIAS) & base.politica.isin(["A", "B", "C"])].assign(variante="reta_x_fator")
    base["esperas"] = [[0.0]] * len(base)  # P90 não comparado nesta análise
    df = pd.concat([df, base], ignore_index=True)
    df["periodo"] = "outubro_4_dias"
    _save(df, "viario")
    s = summarize(df)
    s.to_csv(OUT / "viario_resumo.csv", index=False)
    print(s[["variante", "CxA_km_pct", "CxA_dN", "CxB_km_pct", "CxB_dN", "A_atend_pct", "C_atend_pct"]].to_string())
    print(df[df.variante == "viario_osm"].groupby("dia")[["pontos_ligados", "pontos_a_mais_de_500m_da_rede"]].max().to_string())


# ---------------------------------------------------------------- sintético (P4; sem dados privados)
SINT = Path("reports/synthetic/dispatch_evaluation")
SINT_REDUNDANTES = ("salto6km", "salto10km", "previsao_perfeita", "erro_previsao")  # só alteram o planejador D+1, não o despacho


def cmd_sintetico() -> None:
    df = pd.concat([pd.read_parquet(f) for f in sorted(SINT.glob("cen=*.parquet"))], ignore_index=True)
    df["politica"] = df.politica.replace({"R0": "A", "D_lote60s_guloso_fifo": "B", "D_lote60s_hungaro": "C"})
    df = df[df.politica.isin(["A", "B", "C"])]
    rows = []
    for cen, g in df.groupby("cenario"):
        w = g.pivot_table(index="semente", columns="politica", values=["km_vazio_total", "atendidos"])
        ca = 100 * (w.km_vazio_total.C - w.km_vazio_total.A) / w.km_vazio_total.A
        cb = 100 * (w.km_vazio_total.C - w.km_vazio_total.B) / w.km_vazio_total.B
        dn = w.atendidos.C - w.atendidos.A
        grupo = (
            "principal"
            if cen in ("S1", "S2", "S3", "S4", "S5")
            else "frota"
            if "frota" in cen
            else "zoneamento_do_gerador"
            if "_res" in cen
            else "redundante_para_o_despacho"
        )
        rows.append(
            {
                "cenario": cen,
                "grupo": grupo,
                "sementes": len(w),
                "CxA_pct_mediana": ca.median(),
                "CxA_pct_p10": ca.quantile(0.1),
                "CxA_pct_p90": ca.quantile(0.9),
                "CxA_pct_min": ca.min(),
                "CxA_pct_max": ca.max(),
                "CxA_sementes_com_reducao": int((ca < 0).sum()),
                "CxB_pct_mediana": cb.median(),
                "CxB_pct_p10": cb.quantile(0.1),
                "CxB_pct_p90": cb.quantile(0.9),
                "atendidos_A_medio": w.atendidos.A.mean(),
                "dN_CxA_medio": dn.mean(),
                "sementes_C_atende_menos_que_A": int((dn < 0).sum()),
                "sementes_C_atende_igual_ou_mais": int((dn >= 0).sum()),
                "razao_atendidos_media": float((w.atendidos.C / w.atendidos.A).mean()),
            }
        )
    out = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT / "sintetico_familias.csv", index=False)
    pd.set_option("display.width", 250)
    print(out.round(2).to_string())


if __name__ == "__main__":
    if sys.argv[1] != "sintetico":
        authorize("real")
    {
        "base": cmd_base,
        "sens": cmd_sens,
        "disp": cmd_disp,
        "contagens": cmd_contagens,
        "janelas": cmd_janelas,
        "componentes": cmd_componentes,
        "sintetico": cmd_sintetico,
        "viario": cmd_viario,
        "simulado_a": cmd_simulado_a,
    }[sys.argv[1]]()
