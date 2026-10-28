"""MDE de NB(e*) (80% de poder, 5% bilateral), pelo mesmo método de `fase1_mde.csv`: Z · erro-padrão do bootstrap por dia.

Duas colunas por linha, como na Fase 1: erro-padrão do bootstrap iid e da pior variante (a de maior erro-padrão).
Unidade: corridas equivalentes por dia. Só lê tabelas diárias já agregadas.
"""

from __future__ import annotations

import csv
from math import isfinite
from pathlib import Path

import numpy as np

from . import analise
from . import inferencia as inf
from .fase1 import _intervals, write_csv
from .reamostragem import SCHEMES, indices, scheme_seed

E_MDE = (5, 10, 20, 30, 50)


def mde_rows(pairs: dict, family: str, reps: int = 10000, e_values=E_MDE) -> list[dict]:
    boot: dict[str, dict] = {}
    rows = []
    for key in sorted(pairs):
        pr = pairs[key]
        if key[0] not in boot:
            boot[key[0]] = {s: indices(s, list(pr.dates), reps, scheme_seed(key[0], s)) for s in SCHEMES}
        for e in e_values:
            ivs = _intervals(pr, lambda p, idx=None, e=e: inf.stat_nb(p, e, idx), boot[key[0]])
            ses = [v.se for v in ivs.values() if isfinite(v.se)]
            _, wide = inf.widest(ivs)
            rows.append(
                {
                    "familia": family,
                    "periodo": key[0],
                    "janela": key[1],
                    "grupo_ou_regime": key[2],
                    "cenario": key[3],
                    "dias": len(pr.dates),
                    "e_star_km_por_corrida": e,
                    "nb_corridas_equiv_dia": float(inf.stat_nb(pr, e)),
                    "se_iid": ivs["iid"].se,
                    "mde_nb_iid": inf.mde(ivs["iid"].se),
                    "mde_nb_pior_variante": inf.mde(max(ses)) if ses else float("nan"),
                    "ic_decisao_inf": wide.lo,
                    "ic_decisao_sup": wide.hi,
                }
            )
    return rows


def f1_pairs(dias_csv: Path) -> dict:
    return inf.load_pairs(dias_csv)


def f4_pairs(fase4_dias: Path) -> dict:
    from .fase4 import _is_plan

    with open(fase4_dias, encoding="utf-8", newline="") as h:
        days = list(csv.DictReader(h))
    sel = [
        r
        for r in days
        if r["mundo"] == "origem"
        and r["par"].endswith("rho1")
        and (r["cenario"] == analise.BASE or (r["grupo"].endswith("|c1") and _is_plan(r["cenario"])))
    ]
    return analise.build_pairs(sel, "empty_km", None, "par")


def run(dias_f1: Path, tab11_csv: Path, dias_f4: Path, out: Path, reps: int = 10000) -> dict:
    tab11 = {(r["periodo"], r["janela"], r["regime"], r["cenario"]) for r in csv.DictReader(open(tab11_csv, encoding="utf-8", newline=""))}
    p1 = {k: v for k, v in f1_pairs(dias_f1).items() if k in tab11}
    r1 = mde_rows(p1, "F1", reps)
    write_csv(out / "fase1_mde_nb.csv", r1)
    r4 = mde_rows(f4_pairs(dias_f4), "F4_origem", reps)
    write_csv(out / "fase4_mde_nb.csv", r4)
    summary = {}
    for name, rows in (("F1", r1), ("F4", r4)):
        for e in E_MDE:
            v = [r["mde_nb_pior_variante"] for r in rows if r["e_star_km_por_corrida"] == e]
            summary[f"{name}_e{e}"] = {"linhas": len(v), "mediana_pior": float(np.median(v)), "min": float(min(v)), "max": float(max(v))}
    return summary
