"""Avaliação diária v3: mesmo mundo, planejadores congelados e `simulate3`; demanda do plano pode ser trocada (Fase 3).

Nada aqui altera a v1. Com `demand_mode="previsto"` o resultado reproduz a bateria (regime B). Os modos "oraculo" e
"mistura" usam a demanda real de D+1 e, portanto, **violam o corte D+1**: servem de limite superior, nunca de D+1 estrito.
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import replace
from datetime import date

from tcc_frota.algoritmos.base import PlanContext, PlannerSpec, Scenario, latlon
from tcc_frota.algoritmos.bateria import SEEDS, build_planner, load_frozen, persistent_deficit_zones, build_scenarios
from tcc_frota.algoritmos.protocolo import load_finalists
from tcc_frota.v2 import experiment as ex
from tcc_frota.v2 import forecast as fc
from tcc_frota.v2.fleet import end_of_day
from tcc_frota.v2.sim import SimParams
from tcc_frota.v3.sim import simulate3

REGIME = "B"
ORACLE_ALGORITHMS = ("proporcional", "guloso_a0.02", "guloso_a0.1", "guloso_a0.5", "regra_limiar",
                     "fluxo_custo_minimo", "hungaro", "busca_local", "recozimento", "pso")
DEMAND_DRIVEN = ("proporcional", "guloso_a0.02", "guloso_a0.1", "guloso_a0.5", "regra_limiar", "fluxo_custo_minimo", "hungaro")


def phase3_specs() -> list[PlannerSpec]:
    """Algoritmos e parâmetros congelados (pré-registro D6): três intensidades do guloso, proporcional, limiar e os finalistas."""
    frozen = load_frozen()
    fin = load_finalists()
    g = frozen.selection["guloso_marginal"]
    specs = [PlannerSpec("proporcional", "proporcional", {"max_km": frozen.selection["proporcional"]["max_km"]})]
    specs += [PlannerSpec("guloso_marginal", f"guloso_a{a:g}", {"alpha": a, **g}) for a in (0.02, 0.1, 0.5)]
    specs.append(PlannerSpec("regra_limiar", "regra_limiar", dict(frozen.selection["regra_limiar"])))
    for fam in ("fluxo_custo_minimo", "hungaro", "busca_local", "recozimento", "pso"):
        specs.append(PlannerSpec(fam, fam, fin[fam]["parametros"]))
    return specs


# ---------------------------------------------------------------- demanda real de D+1
def _by_date(study):
    if not hasattr(study, "_v3_demand_by_date"):
        idx = defaultdict(list)
        for (d, h, z), v in study.history.counts.items():
            idx[d].append((h, z, v))
        study._v3_demand_by_date = idx
    return study._v3_demand_by_date


def real_demand(study, target: date, window: tuple[int, int], zones) -> tuple[dict, float]:
    """(λ real por (hora, zona conhecida), demanda real em zonas desconhecidas). Contagens de pedidos (como o alvo da previsão)."""
    known, outside = {}, 0.0
    for h, z, v in _by_date(study).get(target, []):
        if not window[0] <= h < window[1] or not z:
            continue
        if z in zones:
            known[(h, z)] = known.get((h, z), 0.0) + v
        else:
            outside += v
    return known, outside


def mix_demand(y: dict, g: dict, w: float) -> dict:
    keys = set(y) | set(g)
    return {k: (1 - w) * y.get(k, 0.0) + w * g.get(k, 0.0) for k in keys}


def wape_parts(f: dict, y: dict, outside: float) -> tuple[float, float]:
    """(erro absoluto, total real) incluindo a demanda real fora das zonas do plano (erro integral)."""
    keys = set(f) | set(y)
    return sum(abs(f.get(k, 0.0) - y.get(k, 0.0)) for k in keys) + outside, sum(y.values()) + outside


def mixing_weight(target_wape: float, err_g_in: float, y_total: float, outside: float) -> float:
    """w tal que WAPE((1−w)y + w g) = alvo, com WAPE = (w·Σ|g−y|_zonas conhecidas + y_fora) / Σy (D5); limitado a [0, 1]."""
    if err_g_in <= 0:
        return 0.0
    return max(0.0, min(1.0, (target_wape * y_total - outside) / err_g_in))


# ---------------------------------------------------------------- um dia
def _row(key: dict, spec_name: str, family: str, params, res, seed, km_plan: float, secs: float, info: dict, n_drivers: int) -> dict:
    return {**key, "familia": family, "cenario": spec_name, "parametros": json.dumps(params, sort_keys=True), "semente": seed,
            "n_requests": res.n_requests, "served": res.served, "pickup_km": res.pickup_km, "reposition_km": res.reposition_km,
            "empty_km": res.empty_km, "empty_km_sim": res.empty_km_sim, "overnight_km": res.overnight_km,
            "wait_sum": sum(res.wait_s), "moves_planned": res.moves_planned, "moves_executed": res.moves_executed,
            "motoristas_mundo": n_drivers, "km_planejado": km_plan, "plan_seconds": secs, "info": json.dumps(info, default=str)}


def evaluate_day3(study, period: str, target: date, window_key: str, sim: SimParams, specs: list[PlannerSpec], model: str, *,
                  demand_mode: str = "previsto", mix_w: float | None = None, label: str = "", seeds: tuple[int, ...] = SEEDS,
                  include_baseline: bool = True, fix_m1: bool = True, fix_m2: bool = True) -> list[dict]:
    """Baseline e planos em um dia (regime B). `demand_mode`: previsto | oraculo | mistura (usa `mix_w`)."""
    window = ex.WINDOWS[window_key]
    move_mode = ex.EXECUTION[REGIME]
    reqs, drivers = study.world(period, target, window)
    w = (window[0] * 3600.0, window[1] * 3600.0)
    origins = {d.did: p for d in drivers if (p := study.fleet.last_position(d.did, end_of_day(target)))}
    sim_kw = dict(move_mode=move_mode, move_origins=origins, fix_m1=fix_m1, fix_m2=fix_m2)
    base = simulate3(reqs, drivers, sim, w, **sim_kw)
    key = {"periodo": period, "data": target.isoformat(), "janela": window_key, "grupo": label or demand_mode}
    rows = []
    if include_baseline:
        rows.append(_row(key, "sem_reposicionamento", "nenhum", {}, base, "", 0.0, 0.0, {}, len(drivers)))
    inputs, diag = study.plan_inputs(target, window, REGIME, drivers, sim.road_factor, model, fc.ForecastConfig())
    y, outside = real_demand(study, target, window, inputs.zones)
    pred = inputs.demand
    if demand_mode == "oraculo":
        inputs = replace(inputs, demand=mix_demand(y, {}, 0.0))
    elif demand_mode == "mistura":
        inputs = replace(inputs, demand=mix_demand(y, pred, float(mix_w)))
    elif demand_mode != "previsto":
        raise ValueError(demand_mode)
    err, tot = wape_parts(inputs.demand, y, outside)
    diag_row = {"wape_dia_err": err, "wape_dia_total": tot, "demanda_fora_zonas": outside}
    for spec in specs:
        planner = build_planner(spec)
        scenarios = ()
        if getattr(planner, "needs_scenarios", False):
            scenarios = ((Scenario(target, tuple(reqs)),) if demand_mode == "oraculo"
                         else build_scenarios(study, period, target, window, fc.ForecastConfig()))
        extras = {}
        if getattr(planner, "needs_deficit_zones", False):
            extras["zonas_deficit_persistente"] = persistent_deficit_zones(study, target, window, fc.ForecastConfig())
        for seed in (seeds if planner.stochastic else seeds[:1]):
            ctx = PlanContext(inputs, target, window, REGIME, sim, move_mode, scenarios, seed, extras)
            t0 = time.perf_counter()
            moves = planner.plan(ctx)
            secs = time.perf_counter() - t0
            if any(km > planner.max_km + 1e-6 for _, _, km in moves.values()):
                raise AssertionError(f"{spec.name}: movimento além do salto máximo")
            res = simulate3(reqs, drivers, sim, w, latlon(moves), max_move_km=planner.max_km, **sim_kw)
            if res.signature != base.signature:
                raise AssertionError("cenários com entradas diferentes (RN028)")
            rows.append(_row(key, spec.name, spec.family, spec.params, res, seed if planner.stochastic else "",
                             sum(km for _, _, km in moves.values()), secs, {**planner.info, **diag_row}, len(drivers)))
    return rows
