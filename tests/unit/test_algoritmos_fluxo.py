"""5.1/5.2: fluxo de custo mínimo e húngaro com posições de espera."""

from datetime import date

import pytest
from test_v2_policy import instance

from tcc_frota.algoritmos.alvos import largest_remainder, marginal_targets, surplus_deficit, targets
from tcc_frota.algoritmos.base import PlanContext
from tcc_frota.algoritmos.fluxo_custo_minimo import FluxoCustoMinimo, FluxoParametrico
from tcc_frota.v2.fleet import PlannedDriver
from tcc_frota.v2.policy import PlanInputs
from tcc_frota.v2.sim import SimParams, reta_km

SIM = SimParams(4.5, 16.0, 1.3, 180.0)


def ctx(inp, seed=0):
    return PlanContext(inp, date(2026, 3, 16), (4, 11), "B", SIM, "fim_do_dia", (), seed)


def test_targets_sum_and_cap():
    inp = instance(1)
    n = len(inp.drivers)
    assert sum(targets(inp, "demanda", 1.0).values()) == n
    assert all(v <= 2 for v in targets(inp, "teto", 1.3).values())
    assert sum(targets(inp, "valor_marginal", 1.0).values()) <= n
    assert largest_remainder({"a": 1.5, "b": 1.5, "c": 0.0}, 3) in ({"a": 2, "b": 1}, {"a": 1, "b": 2})


def test_marginal_targets_saturate_demand():
    out = marginal_targets({"a": 2.0, "b": 0.5}, 10, per_driver=1.0)
    assert out == {"a": 2, "b": 1}  # depois disso nenhuma vaga acrescenta valor


def test_surplus_deficit_balance():
    sup, dem = surplus_deficit({"a": 3, "b": 0}, {"a": 1, "b": 2, "c": 1})
    assert sup == {"a": 2} and dem == {"b": 2, "c": 1}


@pytest.mark.parametrize("alvo", ["demanda", "valor_marginal", "teto"])
def test_flow_moves_respect_hop_and_are_deterministic(alvo):
    for seed in range(8):
        inp = instance(seed)
        by = {d.did: d for d in inp.drivers}
        planner = FluxoCustoMinimo(alvo, 1.3, 3.0, 2 if alvo == "teto" else None)
        moves = planner.plan(ctx(inp))
        assert moves == planner.plan(ctx(inp, 99))
        for did, (lat, lon, km) in moves.items():
            assert km <= 3.0 + 1e-9
            assert abs(km - reta_km(by[did].lat, by[did].lon, lat, lon) * inp.road_factor) < 1e-9
        assert planner.info["status"] in ("otimo", "sem_arcos")


def test_flow_moves_surplus_to_deficit():
    zones = {"z1": (-20.30, -40.30), "z2": (-20.31, -40.30)}  # ~1,1 km
    drivers = tuple(PlannedDriver(f"d{k}", -20.30, -40.30 + 1e-4 * k, 4, 8) for k in range(2))
    inp = PlanInputs(drivers, zones, {(4, "z2"): 5.0, (4, "z1"): 5.0}, (4,), 1.0, 1.3)
    moves = FluxoCustoMinimo("demanda", 1.0, 3.0).plan(ctx(inp))
    assert len(moves) == 1 and list(moves.values())[0][:2] == zones["z2"]


def test_parametric_min_km_filters_short_moves():
    inp = instance(2)
    loose = FluxoParametrico(0.5, 1.0, 4.0, None, 0.0).plan(ctx(inp))
    strict = FluxoParametrico(0.5, 1.0, 4.0, None, 3.5).plan(ctx(inp))
    assert all(km >= 3.5 for *_, km in strict.values()) and len(strict) <= len(loose)


def _brute_force(inp, slots, zone_of, hop):
    """Máximo de vagas preenchidas e, entre esses, menor km (força bruta em instância pequena)."""
    from itertools import product

    drivers = sorted(inp.drivers, key=lambda d: d.did)
    best = None
    for choice in product(range(-1, len(slots)), repeat=len(drivers)):
        used = [c for c in choice if c >= 0]
        if len(used) != len(set(used)):
            continue
        km = 0.0
        ok = True
        for d, c in zip(drivers, choice):
            if c < 0 or zone_of[d.did] == slots[c]:
                continue
            k = reta_km(d.lat, d.lon, *inp.zones[slots[c]]) * inp.road_factor
            if k > hop:
                ok = False
                break
            km += k
        if ok:
            key = (-len(used), km)
            best = key if best is None or key < best else best
    return best


def test_hungarian_matches_brute_force_on_small_instances():
    from tcc_frota.algoritmos.alvos import driver_zones, targets
    from tcc_frota.algoritmos.hungaro import HungaroPosicoesEspera

    for seed in range(6):
        inp = instance(seed, n_drivers=5, n_zones=4)
        planner = HungaroPosicoesEspera("demanda", 1.0, 6.0)
        moves = planner.plan(ctx(inp))
        slots = [z for z, n in sorted(targets(inp, "demanda", 1.0).items()) for _ in range(n)]
        filled, km = _brute_force(inp, slots, driver_zones(inp), 6.0)
        assert planner.info["vagas_preenchidas"] == -filled
        assert sum(m[2] for m in moves.values()) == pytest.approx(km, abs=1e-6)


def test_hungarian_respects_hop_and_is_deterministic():
    from tcc_frota.algoritmos.hungaro import HungaroPosicoesEspera

    for seed in range(6):
        inp = instance(seed)
        p = HungaroPosicoesEspera("valor_marginal", 1.3, 3.0)
        moves = p.plan(ctx(inp))
        assert moves == p.plan(ctx(inp, 5))
        assert all(km <= 3.0 + 1e-9 for *_, km in moves.values())
