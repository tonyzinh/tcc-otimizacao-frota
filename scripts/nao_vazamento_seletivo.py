"""Teste de não vazamento com dados reais: o plano D+1 do guloso seletivo não muda se os pedidos reais de
D+1 forem alterados (removidos ou trocados pelos de outro dia). Saída: resultados/seletivo/nao_vazamento.json."""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

from tcc_frota.algoritmos.base import PlanContext, PlannerSpec
from tcc_frota.algoritmos.bateria import build_planner, build_scenarios, build_study, load_frozen
from tcc_frota.v2 import experiment as ex
from tcc_frota.v2 import forecast as fc

DAYS = (date(2026, 3, 5), date(2026, 3, 20), date(2026, 9, 22))
PARAMS = {"max_km": 4.0, "k": 8, "tau": 1.0}


def plan_for(study, frozen, period, day):
    window = ex.WINDOWS["04-11"]
    _, drivers = study.world(period, day, window)   # escala de D+1 (premissa do regime B)
    sim = frozen.sims[period]
    inputs, _ = study.plan_inputs(day, window, "B", drivers, sim.road_factor, frozen.model, fc.ForecastConfig())
    scen = build_scenarios(study, period, day, window, fc.ForecastConfig())
    planner = build_planner(PlannerSpec("guloso_seletivo", "x", PARAMS))
    moves = planner.plan(PlanContext(inputs, day, window, "B", sim, "fim_do_dia", scen, 11))
    return moves, planner.info


if __name__ == "__main__":
    os.environ.setdefault("TCC_REAL_DATA_AUTHORIZED", "YES")
    study, frozen = build_study(Path("data/raw")), load_frozen()
    out = []
    for day in DAYS:
        period = "mar2026" if day.month == 3 else "set2026"
        ref, info = plan_for(study, frozen, period, day)
        original = study.requests_by_date[day]
        for label, fake in (("sem_pedidos", []), ("pedidos_de_outro_dia", study.requests_by_date[date(2026, day.month, 2)])):
            study.requests_by_date[day] = [dict(r, data_local=day) for r in fake]
            study._worlds = {k: v for k, v in study._worlds.items() if k[1] != day}
            alt, _ = plan_for(study, frozen, period, day)
            out.append({"dia": day.isoformat(), "alteracao": label, "plano_identico": alt == ref, "movimentos": len(ref),
                        "pares_avaliados": info.get("pares_avaliados")})
            print(out[-1])
        study.requests_by_date[day] = original
        study._worlds = {k: v for k, v in study._worlds.items() if k[1] != day}
    Path("resultados/seletivo/nao_vazamento.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
