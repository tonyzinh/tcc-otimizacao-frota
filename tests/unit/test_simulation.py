from datetime import UTC, datetime, timedelta

import pytest

from tcc_frota.distance import haversine_km
from tcc_frota.evaluation.metrics import compare, summarize
from tcc_frota.models import Commitment, Position, Recommendation, Request, Vehicle
from tcc_frota.simulation.engine import SimulationConfig, simulate

UTC = UTC
START = datetime(2026, 1, 2, 7, tzinfo=UTC)
A = Position("a", -20.30, -40.30)
B = Position("b", -20.31, -40.30)
CONFIG = SimulationConfig(START, START + timedelta(hours=6), speed_kmh=30, max_pickup_minutes=30)


def vehicle(identifier="v", position=A):
    return Vehicle(identifier, position, START, START + timedelta(days=1), modalities=("PF", "PJ"))


def request(identifier="r", at=START + timedelta(hours=1), origin=A, destination=B, minutes=10, modality="PF"):
    return Request(identifier, at, origin, destination, minutes, modality)


def test_events_chronological_and_no_simultaneous_service():
    at = START + timedelta(hours=1)
    result = simulate("baseline", [request("a", at), request("b", at)], [vehicle()], CONFIG)
    assert result.served_ids == ["a"]
    assert result.excluded["unserved_no_eligible_vehicle_or_wait"] == 1
    assert [event.at for event in result.events] == sorted(event.at for event in result.events)
    assert any(event.kind == "trip_end" for event in result.events)


def test_vehicle_released_after_trip_and_midnight_crossing():
    start = datetime(2026, 1, 2, 23, tzinfo=UTC)
    config = SimulationConfig(start, start + timedelta(hours=2))
    v = Vehicle("v", A, start, start + timedelta(hours=3))
    requests = [request("a", start + timedelta(minutes=55), A, A, 15), request("b", start + timedelta(minutes=75), A, A, 10)]
    result = simulate("baseline", requests, [v], config)
    assert len(result.served_ids) == 2
    assert any(e.kind == "trip_end" and e.at.date() > start.date() for e in result.events)


def test_shared_external_commitment_blocks_vehicle_and_unknown_position():
    commitment = Commitment("v", START, START + timedelta(hours=2), "PJ")
    result = simulate(
        "baseline",
        [request(at=START + timedelta(hours=1)), request("later", START + timedelta(hours=3))],
        [vehicle()],
        CONFIG,
        commitments=(commitment,),
    )
    assert result.served_ids == []
    assert result.excluded["unserved_no_eligible_vehicle_or_wait"] == 2
    known = Commitment("v", START, START + timedelta(hours=2), "PJ", B)
    result2 = simulate("baseline", [request("later", START + timedelta(hours=3), B)], [vehicle()], CONFIG, commitments=(known,))
    assert result2.served_ids == ["later"]


def test_future_indisponibility_prevents_assignment_that_would_overlap():
    commitment = Commitment("v", START + timedelta(hours=1, minutes=5), START + timedelta(hours=2), "PJ", B)
    result = simulate(
        "baseline", [request(at=START + timedelta(hours=1), origin=A, minutes=10)], [vehicle()], CONFIG, commitments=(commitment,)
    )
    assert result.served_ids == []
    assert result.excluded["unserved_no_eligible_vehicle_or_wait"] == 1


def test_reposition_included_and_coverage_is_control():
    move = Recommendation("v", A, B, START, haversine_km(A, B))
    r = request(at=START + timedelta(hours=1), origin=B)
    baseline = simulate("baseline", [r], [vehicle()], CONFIG)
    proposed = simulate("proposed", [r], [vehicle()], CONFIG, recommendations=(move,))
    assert proposed.reposition_km > 0
    assert proposed.pickup_km == 0
    assert proposed.km_dead_estimated == pytest.approx(proposed.reposition_km)
    assert summarize(proposed)["observed_km"] is None
    assert compare(baseline, proposed)["comparable_inputs"]


def test_incompatible_conditions_are_rejected():
    r = request()
    baseline = simulate("baseline", [r], [vehicle()], CONFIG)
    changed = simulate("other", [r], [vehicle(position=B)], CONFIG)
    with pytest.raises(ValueError, match="condições iniciais"):
        compare(baseline, changed)
    with pytest.raises(ValueError, match="duplicadas"):
        simulate("bad", [r, r], [vehicle()], CONFIG)


def test_overlap_and_infeasible_reposition_are_rejected():
    c1 = Commitment("v", START, START + timedelta(hours=2), "PJ")
    c2 = Commitment("v", START + timedelta(hours=1), START + timedelta(hours=3), "PF")
    with pytest.raises(ValueError, match="sobrepostos"):
        simulate("bad", [], [vehicle()], CONFIG, commitments=(c1, c2))
    move = Recommendation("v", A, B, START, haversine_km(A, B))
    with pytest.raises(ValueError, match="inviável"):
        simulate("bad", [], [vehicle()], CONFIG, commitments=(c1,), recommendations=(move,))
