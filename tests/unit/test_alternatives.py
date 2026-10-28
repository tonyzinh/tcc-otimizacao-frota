"""Algoritmos alternativos ao guloso: exatidão, limites e comparabilidade."""

import random
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from itertools import permutations

import pytest

from tcc_frota.distance import HaversineDistance
from tcc_frota.models import Position, Request, Vehicle
from tcc_frota.optimization.alternatives import (
    assignment_plan,
    hungarian,
    local_search_plan,
    proportional_plan,
    simulated_greedy_plan,
    target_slots,
)
from tcc_frota.optimization.greedy import _proxy, greedy_plan
from tcc_frota.simulation.engine import SimulationConfig

START = datetime(2026, 9, 30, 10, tzinfo=UTC)
ZONES = {
    "a": Position("a", -20.30, -40.30),
    "b": Position("b", -20.33, -40.30),
    "c": Position("c", -20.30, -40.34),
}
EXPECTED = {"b": 3.0, "c": 1.0}


def fleet(n=4, zone="a"):
    return [Vehicle(f"v{i}", ZONES[zone], START, START + timedelta(hours=3)) for i in range(n)]


def test_hungarian_matches_brute_force():
    rng = random.Random(7)
    for _ in range(30):
        n, m = rng.randint(1, 4), rng.randint(4, 6)
        cost = [[rng.uniform(0, 10) for _ in range(m)] for _ in range(n)]
        columns = hungarian(cost)
        assert len(set(columns)) == n
        best = min(sum(cost[i][p[i]] for i in range(n)) for p in permutations(range(m), n))
        assert sum(cost[i][c] for i, c in enumerate(columns)) == pytest.approx(best)


def test_target_slots_proportional_and_bounded_by_fleet():
    assert target_slots(EXPECTED, 1.0, 10) == {"b": 3, "c": 1}
    assert sum(target_slots(EXPECTED, 1.0, 2).values()) == 2
    assert target_slots({"b": 0.0}, 1.0, 5) == {}
    with pytest.raises(ValueError):
        target_slots(EXPECTED, 0, 3)


@pytest.mark.parametrize("planner", [proportional_plan, assignment_plan])
def test_slot_planners_respect_reposition_limit(planner):
    plan = planner(fleet(), ZONES, EXPECTED, START, capacity_per_vehicle=1.0, max_reposition_km=3.5)
    assert plan.recommendations and all(r.distance_km <= 3.5 for r in plan.recommendations)
    assert {r.destination.zone for r in plan.recommendations} == {"b"}  # c fica a 4,2 km
    none = planner(fleet(), ZONES, EXPECTED, START, capacity_per_vehicle=1.0, max_reposition_km=0.5)
    assert none.recommendations == ()


def test_exact_assignment_never_moves_more_than_proportional_rule():
    vehicles = [
        Vehicle("v0", ZONES["b"], START, START + timedelta(hours=3)),
        Vehicle("v1", ZONES["c"], START, START + timedelta(hours=3)),
        Vehicle("v2", ZONES["a"], START, START + timedelta(hours=3)),
    ]
    kwargs = dict(capacity_per_vehicle=1.0, max_reposition_km=10.0)
    exact = assignment_plan(vehicles, ZONES, {"b": 1.0, "c": 1.0}, START, **kwargs)
    rule = proportional_plan(vehicles, ZONES, {"b": 1.0, "c": 1.0}, START, **kwargs)
    assert exact.reposition_km <= rule.reposition_km + 1e-9
    assert exact.recommendations == ()


def test_local_search_never_worse_than_greedy_on_its_objective():
    vehicles = fleet(3) + [Vehicle("w", ZONES["c"], START, START + timedelta(hours=3))]
    greedy = greedy_plan(vehicles, ZONES, EXPECTED, START, capacity_per_vehicle=1.0)
    plan = local_search_plan(
        vehicles, ZONES, EXPECTED, START, initial=greedy, capacity_per_vehicle=1.0, max_reposition_km=15.0, iterations=300, seed=1
    )
    assert plan.projected_pickup_km + plan.reposition_km <= greedy.projected_pickup_km + greedy.reposition_km + 1e-9


def line(x_km):
    return Position(f"x{x_km}", -20.30 - x_km * 0.008993, -40.30)


def test_simulated_greedy_gains_only_by_correcting_myopic_dispatch():
    """Em linha reta, mover e depois atender custa o mesmo que atender direto (desigualdade
    triangular). O ganho aparece quando o despacho do mais próximo faz uma escolha míope."""
    zones = {"x5": line(5), "x10": line(10)}
    vehicles = [Vehicle("v0", line(0), START, START + timedelta(hours=3)), Vehicle("v1", line(9), START, START + timedelta(hours=3))]
    scenario = [
        Request("r0", START + timedelta(minutes=30), line(5), line(5), 60.0),
        Request("r1", START + timedelta(minutes=31), line(10), line(10), 60.0),
    ]
    config = SimulationConfig(START, START + timedelta(hours=3), speed_kmh=60, max_pickup_minutes=30)
    plan = simulated_greedy_plan(
        vehicles, zones, {"x5": 1.0, "x10": 1.0}, START, scenarios=[scenario], sim_config=config, max_reposition_km=10.0
    )
    assert plan.recommendations
    assert plan.projected_pickup_km + plan.reposition_km < plan.baseline_projected_pickup_km - 1.0
    assert plan.projected_coverage >= plan.baseline_projected_coverage
    assert (
        simulated_greedy_plan(vehicles, zones, {"x5": 1.0}, START, scenarios=[], sim_config=config, max_reposition_km=10.0).recommendations
        == ()
    )


def test_proxy_is_reported_consistently_for_alternatives():
    plan = proportional_plan(fleet(), ZONES, EXPECTED, START, capacity_per_vehicle=1.0, max_reposition_km=10.0)
    positions = {v.vehicle_id: v.position for v in fleet()}
    for r in plan.recommendations:
        positions[r.vehicle_id] = r.destination
    pickup, _ = _proxy(positions, EXPECTED, ZONES, 1.0, 15.0, HaversineDistance())
    assert plan.projected_pickup_km == pytest.approx(pickup)


def test_replay_runs_every_algorithm_with_identical_inputs():
    from tcc_frota.gold.replay import ALGORITHMS, GoldData, run_day
    from tests.unit.test_gold_replay import CONFIG, TARGET, tables

    data = GoldData.from_rows(tables())
    signatures = set()
    for algorithm in ALGORITHMS:
        result = run_day(data, TARGET, replace(CONFIG, algorithm=algorithm), details=True)
        assert result["algorithm"] == algorithm and result["comparable_inputs"] is True
        assert "zonas" in result["details"] and result["plan"]["plan_seconds"] >= 0
        signatures.add((result["baseline"]["estimated_km_dead_total"], result["baseline"]["requests"]))
    assert len(signatures) == 1
    with pytest.raises(ValueError):
        replace(CONFIG, algorithm="inexistente")
