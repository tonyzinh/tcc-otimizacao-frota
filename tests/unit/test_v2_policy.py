"""Algoritmos v2 (Fase 5): propriedades do guloso de valor marginal, da regra de limiar e do proporcional."""

import random

from tcc_frota.v2.fleet import PlannedDriver
from tcc_frota.v2.policy import PlanInputs, marginal_greedy, proportional, threshold_rule
from tcc_frota.v2.sim import reta_km


def instance(seed: int, n_drivers: int = 25, n_zones: int = 12) -> PlanInputs:
    rng = random.Random(seed)
    zones = {f"z{k}": (-20.30 + rng.uniform(-0.08, 0.08), -40.30 + rng.uniform(-0.08, 0.08)) for k in range(n_zones)}
    hours = (4, 5, 6, 7)
    demand = {(h, z): rng.choice([0, 0, 0.5, 2, 5]) for h in hours for z in zones}
    drivers = tuple(
        PlannedDriver(f"d{k}", -20.30 + rng.uniform(-0.1, 0.1), -40.30 + rng.uniform(-0.1, 0.1), rng.uniform(4, 6), rng.uniform(7, 8))
        for k in range(n_drivers)
    )
    return PlanInputs(drivers, zones, demand, hours, kappa=0.8, road_factor=1.4)


ALPHAS = (0.0, 0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 1.0, 2.0, 100.0)


def test_greedy_balance_invariant_and_infinite_price():
    """Garantido: cada passo tem ganho >= α·km, logo ganho total >= α·km total; α grande => nenhum movimento."""
    for seed in range(30):
        inp = instance(seed)
        for a in ALPHAS:
            plan = marginal_greedy(inp, alpha=a, rho_km=1.5, max_km=8.0)
            assert plan.expected_gain >= a * plan.planned_km - 1e-9
        assert marginal_greedy(inp, alpha=100.0, rho_km=1.5, max_km=8.0).moves == {}


def test_greedy_is_approximately_monotone_in_alpha():
    """O guloso não garante monotonicidade; medimos: aumentos de km entre α vizinhos são raros e pequenos."""
    pairs = increases = 0
    worst = 0.0
    for seed in range(100):
        inp = instance(seed)
        kms = [marginal_greedy(inp, alpha=a, rho_km=1.5, max_km=8.0).planned_km for a in ALPHAS]
        for a, b in zip(kms, kms[1:]):
            pairs += 1
            if b > a + 1e-9:
                increases += 1
                worst = max(worst, (b - a) / a)
        assert kms[0] >= kms[-1]
    assert increases / pairs <= 0.05 and worst <= 0.15, (increases, pairs, worst)


def test_no_move_beyond_distance_limit_and_each_driver_moves_once():
    for seed in range(10):
        inp = instance(seed)
        by = {d.did: d for d in inp.drivers}
        for plan in (
            marginal_greedy(inp, alpha=0.01, rho_km=1.5, max_km=3.0),
            threshold_rule(inp, theta=0.01, rho_km=1.5, max_km=3.0),
            proportional(inp, max_km=3.0),
        ):
            for did, (lat, lon) in plan.moves.items():
                assert reta_km(by[did].lat, by[did].lon, lat, lon) * inp.road_factor <= 3.0 + 1e-9


def test_planners_are_deterministic():
    inp = instance(3)
    assert marginal_greedy(inp, alpha=0.1, rho_km=1.5, max_km=6).moves == marginal_greedy(inp, alpha=0.1, rho_km=1.5, max_km=6).moves
    assert threshold_rule(inp, theta=0.1, rho_km=1.5, max_km=6).moves == threshold_rule(inp, theta=0.1, rho_km=1.5, max_km=6).moves


def test_threshold_rule_respects_theta():
    inp = instance(5)
    loose = threshold_rule(inp, theta=0.0, rho_km=1.5, max_km=8)
    strict = threshold_rule(inp, theta=1e6, rho_km=1.5, max_km=8)
    assert strict.moves == {} and len(loose.moves) >= len(strict.moves)


def test_greedy_stops_when_no_positive_balance():
    inp = PlanInputs((PlannedDriver("a", -20.30, -40.30, 4, 8),), {"z": (-20.30, -40.30)}, {(4, "z"): 3.0}, (4,), 1.0, 1.4)
    assert marginal_greedy(inp, alpha=0.0, rho_km=1.5, max_km=10).moves == {}
