"""Controle positivo e controles negativos sintéticos (D12/D13). Sem dados reais; ver `controle.py`."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from tcc_frota.v3 import analise, avaliacao as av, controle as c
from tcc_frota.v3.fase1 import write_csv

EXPERIMENTS = {      # nome: (zona quente, previsão entregue, movimentos nulos)
    "positivo": ("fixa", "verdadeira", False),
    "negativo_previsao_sem_informacao": ("sorteada", "uniforme", False),
}


def collect(exp: str, scenario: str, specs) -> list[dict]:
    mode, forecast, null_move = EXPERIMENTS[exp]
    rows = []
    for i in range(c.N_DAYS):
        rows += c.run_day(i, scenario, specs, mode=mode, forecast=forecast, null_move=null_move)
    return rows


def nulls(specs) -> list[dict]:
    """N1 (baseline × baseline) e N2 (alvo = posição atual): devem dar Δ exatamente zero."""
    out = []
    for scenario in c.SCENARIOS:
        rows = []
        for i in range(c.N_DAYS):
            rows += c.run_day(i, scenario, specs[:1], mode="fixa", forecast="verdadeira", null_move=True)
        base = {r["data"]: r for r in rows if r["cenario"] == analise.BASE}
        plan = [r for r in rows if r["cenario"] != analise.BASE]
        d_n = max(abs(float(r["served"]) - float(base[r["data"]]["served"])) for r in plan)
        d_e = max(abs(float(r["empty_km"]) - float(base[r["data"]]["empty_km"])) for r in plan)
        again = {}
        for i in range(c.N_DAYS):
            again.update({r["data"]: r for r in c.run_day(i, scenario, specs[:0], mode="fixa", forecast="verdadeira")})
        out.append({"controle": "N1_baseline_vs_baseline", "cenario": scenario, "dias": c.N_DAYS,
                    "movimentos_executados": 0, "max_abs_delta_atendidas": max(abs(float(again[d]["served"]) - float(b["served"])) for d, b in base.items()),
                    "max_abs_delta_km_vazio": max(abs(float(again[d]["empty_km"]) - float(b["empty_km"])) for d, b in base.items()),
                    "nota": "duas execuções independentes do baseline (determinismo)"})
        out.append({"controle": "N2_mover_para_onde_ja_esta", "cenario": scenario, "dias": c.N_DAYS,
                    "movimentos_executados": sum(float(r["moves_executed"]) for r in plan),
                    "max_abs_delta_atendidas": d_n, "max_abs_delta_km_vazio": d_e, "nota": "alvo = posição atual"})
    return out


def run(out: Path, reps: int = 10000) -> dict:
    specs = av.phase3_specs()
    summary = {}
    all_days = []
    for exp in EXPERIMENTS:
        for scenario in c.SCENARIOS:
            days = analise.average_seeds(collect(exp, scenario, specs))
            for r in days:
                r["grupo"] = f"{exp}|{scenario}"
            all_days += days
            res = analise.analyze(analise.build_pairs(days, "empty_km"), reps, f"controle_{exp}_{scenario}")
            for name in ("linhas", "nb", "mde"):
                write_csv(out / f"fase2_controle_{exp}_{scenario}_{name}.csv", res[name])
            summary[f"{exp}|{scenario}"] = {d: sum(1 for x in res["linhas"] if x["decisao"] == d) for d in ("reducao", "aumento", "inconclusivo")}
    write_csv(out / "fase2_controle_dias.csv", all_days)
    write_csv(out / "fase2_controle_nulos.csv", nulls(specs))
    return summary
