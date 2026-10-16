"""Experimentos fora da tabela principal: 5.9 MPC intradiário e 5.11 despacho D+0 (e combinações).

Mesmo mundo e mesmo baseline da bateria principal (o simulador estendido sem ganchos reproduz o da v2).
Rotulagem obrigatória: "Cenário intradiário" (5.9) e "D+0" (5.11). Variantes que reduzem KM recusando
corridas aparecem sempre com o atendimento ao lado e não são chamadas de melhoria.
"""
from __future__ import annotations

import json
import time

from tcc_frota.algoritmos.base import PlanContext, PlannerSpec, latlon
from tcc_frota.algoritmos.mpc import epoch_times, plan_epoch
from tcc_frota.algoritmos.sim_estendido import simulate_ext
from tcc_frota.v2 import experiment as ex
from tcc_frota.v2 import forecast as fc
from tcc_frota.v2.fleet import end_of_day
from tcc_frota.v2.sim import simulate


def _metrics(res, n_drivers: int) -> dict:
    return {"n_requests": res.n_requests, "served": res.served, "pickup_km": res.pickup_km,
            "reposition_km": res.reposition_km, "empty_km": res.empty_km, "wait_sum": sum(res.wait_s),
            "moves_planned": res.moves_planned, "moves_executed": res.moves_executed,
            "motoristas_mundo": n_drivers, "signature": res.signature}


def evaluate_day_ext(study, period, target, window_key, regime, sim, specs: list[PlannerSpec], model,
                     seeds=(0,), include_baseline=True) -> list[dict]:
    """`spec.family` ∈ {"mpc", "despacho", "combinado"}; ver docstring do módulo."""
    from tcc_frota.algoritmos.bateria import build_planner, build_scenarios

    window = ex.WINDOWS[window_key]
    w = (window[0] * 3600.0, window[1] * 3600.0)
    reqs, drivers = study.world(period, target, window)
    base = simulate(reqs, drivers, sim, w)
    key = {"periodo": period, "data": target.isoformat(), "janela": window_key, "regime": regime}
    rows = []
    if include_baseline:
        rows.append({**key, "familia": "nenhum", "cenario": "sem_reposicionamento", "parametros": "{}", "semente": "",
                     **_metrics(base, len(drivers)), "km_planejado": 0.0, "plan_seconds": 0.0, "info": "{}"})
    inputs, _ = study.plan_inputs(target, window, regime, drivers, sim.road_factor, model, fc.ForecastConfig())
    origins = {d.did: p for d in drivers if (p := study.fleet.last_position(d.did, end_of_day(target)))}
    for spec in specs:
        p = spec.params
        start = time.perf_counter()
        info = {}
        if spec.family == "mpc":
            elapsed = [0.0]

            def planner(t, idle, busy, _p=p):
                s = time.perf_counter()
                out = plan_epoch(t, idle, busy, inputs, window, horizon_h=_p["horizonte_h"], alpha=_p["alpha"],
                                 rho_km=_p.get("rho_km", 2.5), max_km=_p["max_km"])
                elapsed[0] += time.perf_counter() - s
                return out

            res = simulate_ext(reqs, drivers, sim, w, max_move_km=p["max_km"], epochs=epoch_times(window),
                               epoch_planner=planner)
            plan_s = elapsed[0]
        elif spec.family == "despacho":
            res = simulate_ext(reqs, drivers, sim, w, dispatch="lote", batch_s=p["lote_s"],
                               dispatch_radius_km=sim.radius_km + p["delta_raio_km"])
            plan_s = 0.0
        elif spec.family == "combinado":
            inner = build_planner(PlannerSpec(p["reposicionamento"]["familia"], "inner", p["reposicionamento"]["parametros"]))
            scen = build_scenarios(study, period, target, window, fc.ForecastConfig()) if getattr(inner, "needs_scenarios", False) else ()
            ctx = PlanContext(inputs, target, window, regime, sim, ex.EXECUTION[regime], scen, seeds[0])
            moves = inner.plan(ctx)
            plan_s = time.perf_counter() - start
            res = simulate_ext(reqs, drivers, sim, w, latlon(moves), max_move_km=inner.max_km,
                               move_mode=ex.EXECUTION[regime], move_origins=origins, dispatch="lote",
                               batch_s=p["despacho"]["lote_s"],
                               dispatch_radius_km=sim.radius_km + p["despacho"]["delta_raio_km"])
            info = {"movimentos_plano": len(moves)}
        else:
            raise ValueError(spec.family)
        if res.signature != base.signature:
            raise AssertionError("cenários com entradas diferentes (RN028)")
        rows.append({**key, "familia": spec.family, "cenario": spec.name, "parametros": json.dumps(p, sort_keys=True),
                     "semente": "", **_metrics(res, len(drivers)), "km_planejado": res.reposition_km,
                     "plan_seconds": plan_s, "info": json.dumps(info)})
    return rows


def grid_extra(kind: str) -> list[PlannerSpec]:
    if kind == "mpc":
        return [PlannerSpec("mpc", f"mpc|H{h:g}h|a{a:g}", {"horizonte_h": h, "alpha": a, "rho_km": 2.5, "max_km": 3.0})
                for h in (1.0, 2.0) for a in (0.2, 0.5)]
    if kind == "despacho":
        return [PlannerSpec("despacho", f"despacho|lote{b:g}s|raio{dr:+g}", {"lote_s": b, "delta_raio_km": dr})
                for b in (30.0, 60.0) for dr in (0.0, -1.0)]
    raise ValueError(kind)

