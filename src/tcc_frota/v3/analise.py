"""Inferência genérica (mesmos métodos da Fase 1) sobre linhas diárias de qualquer experimento v3.

Entrada: linhas por (período, dia, grupo, cenário) com métricas somadas no dia (sementes já promediadas). O baseline é o
cenário `sem_reposicionamento` do mesmo (período, dia). `empty_field` escolhe a contabilização: `empty_km` (v1) ou `empty_km_sim`.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from math import isfinite

import numpy as np

from . import inferencia as inf
from .fase1 import ALPHA, E_STAR, _intervals, family_pvalues
from .reamostragem import SCHEMES, indices, scheme_seed

BASE = "sem_reposicionamento"
NUM = ("n_requests", "served", "pickup_km", "reposition_km", "drift_km", "empty_km", "empty_km_sim", "overnight_km", "wait_sum",
       "moves_planned", "moves_executed", "km_planejado")


def average_seeds(rows: list[dict]) -> list[dict]:
    """Média das sementes por (período, data, janela, grupo, cenário)."""
    acc: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        acc[(r["periodo"], r["data"], r["janela"], r["grupo"], r["cenario"])].append(r)
    out = []
    for (periodo, data, janela, grupo, cenario), rs in acc.items():
        row = {"periodo": periodo, "data": data, "janela": janela, "grupo": grupo, "cenario": cenario, "familia": rs[0]["familia"],
               "sementes": len(rs)}
        for extra in ("par", "mundo"):
            if extra in rs[0]:
                row[extra] = rs[0][extra]
        for f in NUM:
            row[f] = sum(float(r.get(f, 0.0) or 0.0) for r in rs) / len(rs)
        out.append(row)
    return out


def build_pairs(days: list[dict], empty_field: str, base_group: str | None = None, match_field: str | None = None) -> dict[tuple, inf.Pairs]:
    """Pares plano × baseline por (período, janela, grupo, cenário). O baseline pode vir de outro grupo (`base_group`)."""
    base = {}
    mk = (lambda r: r[match_field]) if match_field else (lambda r: None)
    for r in days:
        if r["cenario"] == BASE and (base_group is None or r["grupo"] == base_group):
            base[(r["periodo"], r["data"], r["janela"], mk(r))] = r
    plans: dict[tuple, dict[str, dict]] = defaultdict(dict)
    for r in days:
        if r["cenario"] != BASE:
            plans[(r["periodo"], r["janela"], r["grupo"], r["cenario"])][r["data"]] = r
    out = {}
    for key, by_day in plans.items():
        ds = sorted(by_day)
        bs = [base[(key[0], d, key[1], mk(by_day[d]))] for d in ds]

        def arrays(rs):
            a = {k: np.array([float(r[k]) for r in rs]) for k in inf.FIELDS if k != "empty_km"}
            a["empty_km"] = np.array([float(r[empty_field]) for r in rs])
            return a
        out[key] = inf.Pairs(key, tuple(date.fromisoformat(d) for d in ds), arrays(bs), arrays([by_day[d] for d in ds]))
    return out


def analyze(pairs: dict[tuple, inf.Pairs], reps: int = 10000, family: str = "", tests: bool = True) -> dict[str, list[dict]]:
    """Mesmo pipeline da Fase 1 sobre `pairs` (uma família = todas as chaves dadas)."""
    keys = sorted(pairs)
    boot: dict[str, dict[str, np.ndarray]] = {}
    for periodo in sorted({k[0] for k in keys}):
        dates = pairs[next(k for k in keys if k[0] == periodo)].dates
        boot[periodo] = {s: indices(s, list(dates), reps, scheme_seed(periodo, s)) for s in SCHEMES}
    rows = []
    for key in keys:
        pr, bi = pairs[key], boot[key[0]]
        if len(pr.dates) != len(boot[key[0]]["iid"][0]):
            raise ValueError("períodos com números de dias diferentes entre chaves")
        r = {"key": key, "pr": pr, "km": _intervals(pr, inf.stat_km_vazio_pct, bi), "n_pct": _intervals(pr, inf.stat_served_pct, bi),
             "dn": _intervals(pr, inf.stat_d_served_day, bi), "de": _intervals(pr, inf.stat_d_empty_day, bi)}
        for e in E_STAR:
            r[f"nb{e}"] = _intervals(pr, lambda p, idx=None, e=e: inf.stat_nb(p, e, idx), bi)
        rows.append(r)
    if tests:
        red, aum = family_pvalues(rows, "reducao", "km"), family_pvalues(rows, "aumento", "km")
        ni, ni2 = family_pvalues(rows, "nao_inferior", "n_pct"), family_pvalues(rows, "nao_inferior_sens", "n_pct")
    else:     # análise descritiva (sem p-valores): usado na grade ρ × conformidade
        nan = {k: np.full(len(rows), np.nan) for k in ("raw", "holm", "rw")}
        red = aum = ni = ni2 = nan
    lines, nb_rows, mde_rows = [], [], []
    for i, r in enumerate(rows):
        key = r["key"]
        base = {"familia_testes": family, "periodo": key[0], "janela": key[1], "grupo": key[2], "cenario": key[3], "dias": len(r["pr"].dates)}
        k_name, k_iv = inf.widest(r["km"])
        _, n_iv = inf.widest(r["n_pct"])
        ok1 = isfinite(n_iv.lo) and n_iv.lo >= inf.NON_INFERIORITY_PP
        ok2 = isfinite(n_iv.lo) and n_iv.lo >= inf.NON_INFERIORITY_SENS_PP
        if not tests:
            decisao = "descritivo"
        elif red["rw"][i] < ALPHA and k_iv.hi < 0 and ok1:
            decisao = "reducao"
        elif aum["rw"][i] < ALPHA and k_iv.lo > 0:
            decisao = "aumento"
        else:
            decisao = "inconclusivo"
        lines.append({**base, "km_vazio_pct": k_iv.point, "ic_decisao_inf": k_iv.lo, "ic_decisao_sup": k_iv.hi, "ic_decisao_variante": k_name,
                      "p_bruto_reducao": red["raw"][i], "p_holm_reducao": red["holm"][i], "p_rw_reducao": red["rw"][i],
                      "p_bruto_aumento": aum["raw"][i], "p_rw_aumento": aum["rw"][i],
                      "atendidas_pct": n_iv.point, "atendidas_ic_inf": n_iv.lo, "atendidas_ic_sup": n_iv.hi,
                      "p_rw_nao_inferior_1pp": ni["rw"][i], "p_rw_nao_inferior_2pp": ni2["rw"][i],
                      "nao_inferior_1pp_ic": ok1, "nao_inferior_2pp_ic": ok2,
                      "d_atendidas_dia": r["dn"]["iid"].point, "d_km_vazio_dia": r["de"]["iid"].point, "decisao": decisao})
        for e in E_STAR:
            name, iv = inf.widest(r[f"nb{e}"])
            nb_rows.append({**base, "e_star": e, "nb": iv.point, "ic_inf": iv.lo, "ic_sup": iv.hi,
                            "conclusao": "NB>0" if iv.lo > 0 else ("NB<0" if iv.hi < 0 else "inconclusivo")})
        km_se = [v.se for v in r["km"].values() if isfinite(v.se)]
        n_se = [v.se for v in r["n_pct"].values() if isfinite(v.se)]
        mde_rows.append({**base, "mde_km_vazio_pct": inf.mde(max(km_se)) if km_se else float("nan"),
                         "mde_atendidas_pct": inf.mde(max(n_se)) if n_se else float("nan")})
    return {"linhas": lines, "nb": nb_rows, "mde": mde_rows}
