from datetime import UTC, datetime, timedelta

import pytest

from tcc_frota.models import Commitment, Position, Vehicle
from tcc_frota.optimization.greedy import greedy_plan

START = datetime(2026, 1, 2, 7, tzinfo=UTC)
A = Position("a", -20.30, -40.30)
B = Position("b", -20.33, -40.28)


def vehicle(identifier="v", *, active=True, ready=True, position=A):
    return Vehicle(identifier, position, START, START + timedelta(hours=4), active, ready)


def test_no_fleet_no_demand_and_ineligible():
    assert greedy_plan([], {"a": A}, {"a": 2}, START).recommendations == ()
    assert greedy_plan([vehicle()], {"a": A}, {"a": 0}, START).recommendations == ()
    assert greedy_plan([vehicle(active=False), vehicle("x", ready=False)], {"a": A}, {"a": 2}, START).recommendations == ()


def test_greedy_counts_reposition_and_deterministic_tie():
    fleet = [vehicle("b"), vehicle("a")]
    result = greedy_plan(fleet, {"a": A, "b": B}, {"b": 4}, START, max_pickup_km=20)
    assert result.recommendations
    assert result.recommendations[0].vehicle_id == "a"
    assert result.reposition_km > 0
    assert result.projected_pickup_km + result.reposition_km < result.baseline_projected_pickup_km
    assert result == greedy_plan(list(reversed(fleet)), {"a": A, "b": B}, {"b": 4}, START, max_pickup_km=20)


def test_costly_or_conflicting_move_is_rejected():
    assert not greedy_plan([vehicle()], {"a": A, "b": B}, {"b": 1}, START).recommendations
    commitment = Commitment("v", START + timedelta(minutes=1), START + timedelta(hours=2), "PJ", B)
    assert not greedy_plan([vehicle()], {"a": A, "b": B}, {"b": 4}, START, commitments=(commitment,)).recommendations


def test_minimum_coverage_is_experimental_constraint():
    result = greedy_plan([vehicle()], {"a": A, "b": B}, {"b": 8}, START, capacity_per_vehicle=1, min_coverage=1)
    assert not result.recommendations
    assert result.projected_coverage < 1
    with pytest.raises(ValueError):
        greedy_plan([vehicle()], {"a": A}, {"a": 1}, START, min_coverage=1.2)
