"""Controles sintéticos da v2 (D12): positivo ("fácil"), nulo contra nulo, mover para onde já está e previsão sem informação.

Mundo 100% sintético: nenhum dado real. Serve para checar que o simulador e a cadeia de inferência *conseguem* registrar um
ganho quando ele existe por construção. Planejadores, parâmetros e inferência são os mesmos das Fases 1 e 3.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta

import numpy as np

from tcc_frota.algoritmos.base import PlanContext, Scenario, latlon
from tcc_frota.algoritmos.bateria import build_planner
from tcc_frota.v2.fleet import PlannedDriver
from tcc_frota.v2.policy import PlanInputs
from tcc_frota.v2.sim import SimDriver, SimParams, SimRequest
from tcc_frota.v3.sim import simulate3

LAT0, LON0 = -20.30, -40.30
KM_LAT = 111.19
WINDOW = (4, 11)
N_DRIVERS = 12
HOT_RATE, COLD_RATE = 60, 10  # pedidos por dia
HOP_KM = 2.0  # distância reta de C à zona quente
TRIP_S = 600.0
JITTER_KM = 0.3
N_DAYS = 16
N_SCENARIOS = 5
SIDES = {"E": (1, 0), "W": (-1, 0), "N": (0, 1), "S": (0, -1)}
SEEDS = (11, 23, 37, 41, 53)
START = date(2026, 3, 16)

SCENARIOS = {  # raio de despacho em km; os demais parâmetros são os de março (reports/tcc_final/result.json)
    "alcancavel": 4.5,
    "fora_do_raio": 1.5,
}
MARCH = dict(speed_kmh=16.0793020421524, road_factor=1.3012454652253007, patience_s=180.0)


def sim_params(scenario: str) -> SimParams:
    return SimParams(radius_km=SCENARIOS[scenario], **MARCH)


def _pt(dx_km: float, dy_km: float) -> tuple[float, float]:
    return LAT0 + dy_km / KM_LAT, LON0 + dx_km / (KM_LAT * math.cos(math.radians(LAT0)))


def zone_centers() -> dict[str, tuple[float, float]]:
    z = {"C": _pt(0.0, 0.0)}
    for name, (sx, sy) in SIDES.items():
        z[name] = _pt(sx * HOP_KM, sy * HOP_KM)
    return z


def _around(rng: np.random.Generator, center: tuple[float, float], radius_km: float) -> tuple[float, float]:
    r, a = radius_km * math.sqrt(rng.random()), 2 * math.pi * rng.random()
    dx, dy = r * math.cos(a), r * math.sin(a)
    return center[0] + dy / KM_LAT, center[1] + dx / (KM_LAT * math.cos(math.radians(LAT0)))


def hot_side(day_index: int, mode: str) -> str:
    """Lado da zona quente: fixo (E) no controle positivo; sorteado por dia, com semente fixa, nos controles de previsão sem informação."""
    if mode == "fixa":
        return "E"
    return "EWNS"[int(np.random.default_rng(20261028 + day_index).integers(4))]


def make_requests(day_index: int, side: str, salt: int = 0) -> list[SimRequest]:
    rng = np.random.default_rng(1_000_003 * (day_index + 1) + salt)
    zones = zone_centers()
    reqs, rid = [], 0
    for zone, n in ((side, HOT_RATE), ("C", COLD_RATE)):
        for _ in range(int(rng.poisson(n))):
            t = (WINDOW[0] + (WINDOW[1] - WINDOW[0]) * rng.random()) * 3600.0
            lat, lon = _around(rng, zones[zone], JITTER_KM)
            dlat, dlon = _around(rng, zones[zone], 0.5)
            reqs.append(SimRequest(rid, t, lat, lon, dlat, dlon, TRIP_S, None, False, int(t // 3600), zone))
            rid += 1
    reqs.sort(key=lambda r: r.t)
    return [SimRequest(i, r.t, r.lat, r.lon, r.dlat, r.dlon, r.trip_s, None, False, r.hour, r.zone) for i, r in enumerate(reqs)]


def make_fleet(day_index: int) -> tuple[list[SimDriver], dict[str, tuple[float, float]]]:
    rng = np.random.default_rng(7_000_001 + day_index)
    drivers, origins = [], {}
    for k in range(N_DRIVERS):
        lat, lon = _around(rng, zone_centers()["C"], 0.2)
        did = f"s{k:02d}"
        drivers.append(SimDriver(did, ((WINDOW[0] * 3600.0, WINDOW[1] * 3600.0, lat, lon),)))
        origins[did] = (lat, lon)
    return drivers, origins


def plan_inputs(drivers, origins, forecast_sides: dict[str, float], road_factor: float) -> PlanInputs:
    """Previsão entregue ao planejador: taxa por lado (soma = HOT_RATE) mais a demanda fria em C. Taxa verdadeira ou uniforme."""
    hours = tuple(range(*WINDOW))
    nh = len(hours)
    demand = {(h, z): rate / nh for z, rate in forecast_sides.items() for h in hours}
    for h in hours:
        demand[(h, "C")] = COLD_RATE / nh
    zones = {z: p for z, p in zone_centers().items() if z in demand_zones(forecast_sides)}
    planned = tuple(PlannedDriver(d.did, *origins[d.did], float(WINDOW[0]), float(WINDOW[1])) for d in drivers)
    return PlanInputs(planned, zones, demand, hours, 0.9, road_factor)


def demand_zones(sides: dict[str, float]) -> set[str]:
    return set(sides) | {"C"}


def make_scenarios(mode: str, forecast_mode: str, n: int = N_SCENARIOS) -> tuple[Scenario, ...]:
    """Pseudodias independentes do mesmo gerador (anteriores ao alvo). Com previsão sem informação, o lado quente deles também é sorteado."""
    out = []
    for k in range(n):
        idx = 10_000 + k
        side = "E" if forecast_mode == "verdadeira" and mode == "fixa" else hot_side(idx, "sorteada")
        out.append(Scenario(START - timedelta(days=k + 1), tuple(make_requests(idx, side, salt=99))))
    return tuple(out)


def run_day(
    day_index: int, scenario: str, specs, *, mode: str, forecast: str, null_move: bool = False, include_baseline: bool = True
) -> list[dict]:
    """Um dia: baseline sem reposicionamento e um plano por planejador (e semente). `mode`: fixa|sorteada (zona quente);
    `forecast`: verdadeira|uniforme (informação entregue ao planejador). `null_move`: alvos = posição atual (controle N2)."""
    sim = sim_params(scenario)
    side = hot_side(day_index, mode)
    reqs = make_requests(day_index, side)
    drivers, origins = make_fleet(day_index)
    w = (WINDOW[0] * 3600.0, WINDOW[1] * 3600.0)
    kw = dict(move_mode="fim_do_dia", move_origins=origins, fix_m1=True, start_at_origin=True)
    date_ = (START + timedelta(days=day_index)).isoformat()
    key = {"periodo": scenario, "data": date_, "janela": "04-11", "grupo": f"{mode}|{forecast}"}
    base = simulate3(reqs, drivers, sim, w, **kw)
    rows = []

    def row(name, family, res, seed, km_plan):
        return {
            **key,
            "familia": family,
            "cenario": name,
            "semente": seed,
            "n_requests": res.n_requests,
            "served": res.served,
            "pickup_km": res.pickup_km,
            "reposition_km": res.reposition_km,
            "empty_km": res.empty_km,
            "empty_km_sim": res.empty_km_sim,
            "overnight_km": res.overnight_km,
            "wait_sum": sum(res.wait_s),
            "moves_planned": res.moves_planned,
            "moves_executed": res.moves_executed,
            "km_planejado": km_plan,
        }

    if include_baseline:
        rows.append(row("sem_reposicionamento", "nenhum", base, "", 0.0))
    sides = {s: (HOT_RATE if s == side else 0.0) for s in SIDES} if forecast == "verdadeira" else dict.fromkeys(SIDES, HOT_RATE / 4)
    sides = {s: r for s, r in sides.items() if r > 0}
    inputs = plan_inputs(drivers, origins, sides, sim.road_factor)
    scenarios = make_scenarios(mode, forecast)
    for spec in specs:
        planner = build_planner(spec)
        for seed in SEEDS if planner.stochastic else SEEDS[:1]:
            if null_move:
                moves = {d.did: (*origins[d.did], 0.0) for d in drivers}
            else:
                moves = planner.plan(
                    PlanContext(
                        inputs,
                        START + timedelta(days=day_index),
                        WINDOW,
                        "B",
                        sim,
                        "fim_do_dia",
                        scenarios if getattr(planner, "needs_scenarios", False) else (),
                        seed,
                        {},
                    )
                )
            res = simulate3(reqs, drivers, sim, w, latlon(moves), max_move_km=planner.max_km, **kw)
            if res.signature != base.signature:
                raise AssertionError("cenários com entradas diferentes (RN028)")
            rows.append(row(spec.name, spec.family, res, seed if planner.stochastic else "", sum(km for _, _, km in moves.values())))
    return rows


def summarize_hot_share(rows: list[dict]) -> dict:
    """Diagnóstico agregado (sem dados individuais): pedidos e atendidos por cenário."""
    acc = defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        acc[r["cenario"]][0] += float(r["n_requests"])
        acc[r["cenario"]][1] += float(r["served"])
    return {k: {"pedidos": v[0], "atendidos": v[1]} for k, v in acc.items()}
