"""Fase 4: baselines realistas (B0–B4), recuperabilidade (ρ) e conformidade, com contabilização corrigida (m1, m2).

Cada braço = (realocação de início de dia do plano, ou nenhuma) + (política de deriva dos livres Bk). Baseline e plano usam a
mesma política Bk, o mesmo mundo, a mesma fila e os mesmos números aleatórios (sorteios por hash de semente, ID e dia).
O plano é calculado uma vez por (dia, algoritmo, semente) e independe de ρ, conformidade e Bk (o planejador não conhece o baseline).
"""
from __future__ import annotations

import json
import random
import time
import zlib
from datetime import date

from tcc_frota.algoritmos.base import PlanContext, PlannerSpec, Scenario, latlon
from tcc_frota.algoritmos.bateria import SEEDS, build_planner, build_scenarios, persistent_deficit_zones
from tcc_frota.v2 import experiment as ex
from tcc_frota.v2 import forecast as fc
from tcc_frota.v2.fleet import end_of_day, seconds
from tcc_frota.v2.sim import SimParams, reta_km
from tcc_frota.v3.deriva import LocalCruise, ObservedTracks, ReactiveConfig, ReturnHome, observed_pieces
from tcc_frota.v3.sim import simulate3

RHOS = (0.25, 0.5, 0.75, 1.0)
CONFS = (0.5, 0.75, 1.0)
BASELINES = ("B0", "B1", "B2", "B3", "B4")
CRN_SEED = 20261028
REACTIVE = ReactiveConfig(tick_s=300.0, lookback_s=900.0, max_km=3.0)   # parâmetros declarados (pré-registro D10)
REGIME, WINDOW = "B", "04-11"


def u01(*parts) -> float:
    """Uniforme [0,1) determinística (números aleatórios comuns entre braços e cenários)."""
    return (zlib.crc32("|".join(str(p) for p in (CRN_SEED, *parts)).encode()) & 0xFFFFFFFF) / 2**32


def unrecoverable_ids(accepted: dict[int, bool], rho: float) -> frozenset:
    """Pedidos não aceitos que um motorista disponível NÃO aceitaria (fração 1−ρ, monótona em ρ)."""
    return frozenset(rid for rid, ok in accepted.items() if not ok and u01("rho", rid) >= rho)


def complies(did: str, target: date, conf: float) -> bool:
    return u01("conf", did, target.isoformat()) < conf


def observed_tracks(study, target: date, road_factor: float) -> dict[str, tuple]:
    out = {}
    for did, rows in study.fleet.by_date.get(target, {}).items():
        snaps = sorted((seconds(r["ts_snapshot"], target), r["lat"], r["lon"], r["estado"]) for r in rows)
        pieces = observed_pieces(snaps, road_factor)
        if pieces:
            out[did] = pieces
    return out


def policy_args(name: str, tracks: dict) -> dict:
    if name == "B0":
        return {}
    if name == "B1":
        return {"drift": ReturnHome()}
    if name == "B2":
        return {"drift": ObservedTracks(tracks)}
    if name == "B3":
        return {"drift": LocalCruise(2.0, CRN_SEED)}
    if name == "B4":
        return {"reactive": REACTIVE}
    raise ValueError(name)


def _row(key: dict, scen: str, family: str, params, res, seed, km_plan, secs, n_drivers: int) -> dict:
    return {**key, "familia": family, "cenario": scen, "parametros": json.dumps(params, sort_keys=True), "semente": seed,
            "n_requests": res.n_requests, "served": res.served, "pickup_km": res.pickup_km, "reposition_km": res.reposition_km,
            "drift_km": res.drift_km, "empty_km": res.empty_km_v1, "empty_km_sim": res.empty_km_sim, "overnight_km": res.overnight_km,
            "wait_sum": sum(res.wait_s), "moves_planned": res.moves_planned, "moves_executed": res.moves_executed,
            "motoristas_mundo": n_drivers, "km_planejado": km_plan, "plan_seconds": secs}


def placebo_moves(inputs, moves: dict, hop_km: float, seed_key: str) -> dict:
    """Mesma quantidade de movimentos do plano, mas motoristas e alvos aleatórios (alvo = centróide conhecido a <= hop da origem)."""
    rng = random.Random(zlib.crc32(f"{CRN_SEED}|placebo|{seed_key}".encode()))
    zones = list(inputs.zones.values())
    pool = list(inputs.drivers)
    rng.shuffle(pool)
    out = {}
    for d in pool:
        if len(out) >= len(moves):
            break
        cand = [z for z in zones if 0.05 < reta_km(d.lat, d.lon, *z) * inputs.road_factor <= hop_km]
        if cand:
            out[d.did] = rng.choice(cand)
    return out


def evaluate_day4(study, period: str, target: date, sim: SimParams, specs: list[PlannerSpec], model: str, *,
                  world: str = "origem", seeds: tuple[int, ...] = SEEDS, rhos=RHOS, confs=CONFS, baselines=BASELINES,
                  placebo: bool = True) -> list[dict]:
    """`world`: "origem" (m2 primária: os dois braços começam na última posição de D) ou "login" (mundo da v1; traz também a
    contabilização "pagar nos dois", `empty_km_sim`). m1 sempre corrigido. O placebo roda só em ρ = 1 e conformidade = 1."""
    window = ex.WINDOWS[WINDOW]
    move_mode = ex.EXECUTION[REGIME]
    reqs, drivers = study.world(period, target, window)
    w = (window[0] * 3600.0, window[1] * 3600.0)
    origins = {d.did: p for d in drivers if (p := study.fleet.last_position(d.did, end_of_day(target)))}
    accepted = {r["codigo"]: bool(r["fl_aceito"]) for r in study.requests_by_date.get(target, [])}
    tracks = observed_tracks(study, target, sim.road_factor)
    if world == "origem":
        common = dict(move_mode=move_mode, move_origins=origins, fix_m1=True, start_at_origin=True)
    elif world == "login":
        common = dict(move_mode=move_mode, move_origins=origins, fix_m1=True, fix_m2=True)
    else:
        raise ValueError(world)
    inputs, diag = study.plan_inputs(target, window, REGIME, drivers, sim.road_factor, model, fc.ForecastConfig())

    plans = []   # (spec, planner, seed, moves, secs, rótulo)
    for spec in specs:
        planner = build_planner(spec)
        scenarios = build_scenarios(study, period, target, window, fc.ForecastConfig()) if getattr(planner, "needs_scenarios", False) else ()
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
            plans.append((spec, planner, seed, latlon(moves), secs, spec.name))
            if placebo:
                pm = placebo_moves(inputs, moves, planner.max_km, f"{target}|{spec.name}|{seed}")
                plans.append((spec, planner, seed, pm, 0.0, f"placebo_{spec.name}"))

    rows = []
    base_key = {"periodo": period, "data": target.isoformat(), "janela": WINDOW, "mundo": world}
    for rho in rhos:
        unrec = unrecoverable_ids(accepted, rho)
        for bk in baselines:
            pol = policy_args(bk, tracks)
            par = f"{world}|{bk}|rho{rho:g}"
            base = simulate3(reqs, drivers, sim, w, unrecoverable=unrec, **pol, **common)
            rows.append(_row({**base_key, "grupo": "base", "par": par}, "sem_reposicionamento", "nenhum", {}, base, "", 0.0, 0.0, len(drivers)))
            for conf in confs:
                for spec, planner, seed, moves, secs, label in plans:
                    if label.startswith("placebo_") and not (rho == 1.0 and conf == 1.0):
                        continue
                    kept = {did: m for did, m in moves.items() if complies(did, target, conf)}
                    res = simulate3(reqs, drivers, sim, w, kept, max_move_km=planner.max_km, unrecoverable=unrec, **pol, **common)
                    rows.append(_row({**base_key, "grupo": f"{par}|c{conf:g}", "par": par}, label, spec.family, spec.params, res,
                                      seed if planner.stochastic else "", 0.0, secs, len(drivers)))
            if bk != "B4" and rho == 1.0:      # B4 como candidato (sem plano) contra a política Bk
                cand = simulate3(reqs, drivers, sim, w, unrecoverable=unrec, reactive=REACTIVE, **common)
                rows.append(_row({**base_key, "grupo": f"{par}|candidato", "par": par}, "B4_reativo_candidato", "reativo", {}, cand, "", 0.0, 0.0, len(drivers)))
    return rows
