"""Regressão: as referências pela interface `Planner` reproduzem os números diários do artigo.

Compara, dia a dia, corridas atendidas, KM de busca, KM de reposicionamento e movimentos executados
com `individual/dias_cenarios.csv` da execução `final-run` de referência (regimes A e B, janela
04–11h, dias de teste de março e setembro).
"""

from __future__ import annotations

import csv
from pathlib import Path

from tcc_frota.algoritmos.bateria import evaluate_day, load_frozen, reference_specs
from tcc_frota.v2 import experiment as ex

OLD_NAME = {
    "ref_proporcional": "proporcional",
    "ref_regra_limiar": "regra_limiar",
    "ref_guloso_a0.05": "guloso_marginal_a0.05",
    "ref_guloso_a0.2": "guloso_marginal_a0.2",
    "ref_guloso_a0.5": "guloso_marginal_a0.5",
}


def run(study, daily_csv: Path, regimes=("A", "B"), echo=print) -> dict:
    frozen = load_frozen()
    old = {}
    with daily_csv.open(encoding="utf-8") as handle:
        for r in csv.DictReader(handle):
            if r["janela"] == ex.MAIN_WINDOW and r["regime"] in regimes:
                old[(r["periodo"], r["data"], r["regime"], r["cenario"])] = r
    specs = reference_specs(frozen.selection)
    checked = mismatches = 0
    worst = 0.0
    for period, p in ex.PERIODS.items():
        for day in p.test:
            for regime in regimes:
                rows = evaluate_day(study, period, day, ex.MAIN_WINDOW, regime, frozen.sims[period], specs, frozen.model)
                for r in rows:
                    name = OLD_NAME.get(r["cenario"], r["cenario"])
                    o = old[(period, day.isoformat(), regime, name)]
                    checked += 1
                    diffs = [
                        abs(r["served"] - int(o["served"])),
                        abs(r["moves_executed"] - int(o["moves_executed"])),
                        abs(r["pickup_km"] - float(o["pickup_km"])),
                        abs(r["reposition_km"] - float(o["reposition_km"])),
                    ]
                    worst = max(worst, max(diffs))
                    if diffs[0] or diffs[1] or diffs[2] > 1e-3 or diffs[3] > 1e-3:
                        mismatches += 1
                        echo(f"DIVERGE {period} {day} {regime} {name}: {diffs}")
    out = {"linhas_conferidas": checked, "divergencias": mismatches, "maior_diferenca_absoluta": worst}
    echo(f"regressão das referências: {out}")
    return out
