"""Invariantes do simulador com despacho em lotes: sem acesso ao futuro, sem atendimento duplicado, sem teletransporte, conservação de km."""

from __future__ import annotations

import numpy as np
import pytest

from tcc_frota.assignment import dispatch as dp
from tcc_frota.domain.entities import SimDriver, SimParams, SimRequest, reta_km
from tcc_frota.simulation.engine import simulate

PARAMS = SimParams(radius_km=4.5, speed_kmh=30.0, road_factor=1.0, patience_s=180.0)
WINDOW = (0.0, 7200.0)


def _random_world(seed: int, n_req: int = 40, n_drv: int = 8):
    rng = np.random.default_rng(seed)
    reqs = [
        SimRequest(
            rid=i,
            t=float(rng.uniform(0, 3600)),
            lat=-20.3 + rng.uniform(-0.02, 0.02),
            lon=-40.3 + rng.uniform(-0.02, 0.02),
            dlat=-20.3 + rng.uniform(-0.03, 0.03),
            dlon=-40.3 + rng.uniform(-0.03, 0.03),
            trip_s=float(rng.uniform(300, 900)),
        )
        for i in range(n_req)
    ]
    reqs.sort(key=lambda r: (r.t, r.rid))
    drivers = [
        SimDriver(did=f"d{k}", sessions=((0.0, 7200.0, -20.3 + rng.uniform(-0.02, 0.02), -40.3 + rng.uniform(-0.02, 0.02)),))
        for k in range(n_drv)
    ]
    return reqs, drivers


def test_assigner_sees_only_arrived_requests_when_batch_is_decided():
    reqs, drivers = _random_world(1)
    seen = []

    def spy(t, pending, candidates):
        seen.append((t, [r.t for r in pending]))
        return dp.hungarian(t, pending, candidates)

    simulate(reqs, drivers, PARAMS, WINDOW, {}, batch_s=60.0, assigner=spy)
    assert seen, "o assigner deveria ser chamado"
    assert all(max(arrivals) <= t + 1e-9 for t, arrivals in seen if arrivals)
    assert all(abs(t % 60.0) < 1e-9 for t, _ in seen)  # decisões só em múltiplos de 60 s


def test_each_request_is_served_at_most_once_when_policies_are_batched():
    reqs, drivers = _random_world(2)
    res = simulate(reqs, drivers, PARAMS, WINDOW, {}, batch_s=60.0, assigner=dp.hungarian)
    assert res.served <= res.n_requests == len(reqs)
    assert len(res.wait_s) == res.served


def test_empty_km_equals_pickup_plus_repositioning_when_no_plan_is_given():
    reqs, drivers = _random_world(3)
    res = simulate(reqs, drivers, PARAMS, WINDOW, {}, batch_s=60.0, assigner=dp.hungarian)
    assert res.empty_km == res.pickup_km + res.reposition_km
    assert res.reposition_km == 0.0


def test_pickup_km_never_exceeds_radius_times_served_when_dispatch_is_radius_limited():
    reqs, drivers = _random_world(4)
    res = simulate(reqs, drivers, PARAMS, WINDOW, {}, batch_s=60.0, assigner=dp.hungarian)
    assert res.pickup_km <= PARAMS.radius_km * max(res.served, 1) * 1.0000001


def test_wait_is_never_negative_when_requests_are_served():
    reqs, drivers = _random_world(5)
    res = simulate(reqs, drivers, PARAMS, WINDOW, {}, batch_s=60.0, assigner=dp.hungarian)
    assert all(np.isfinite(w) and w >= 0.0 for w in res.wait_s)  # a espera inclui o deslocamento de aproximação


def test_driver_outside_shift_is_not_dispatched_when_request_arrives_after_session_end():
    req = [SimRequest(rid=1, t=500.0, lat=-20.3, lon=-40.3, dlat=-20.31, dlon=-40.31, trip_s=300.0)]
    driver = [SimDriver(did="d", sessions=((0.0, 100.0, -20.3, -40.3),))]
    res = simulate(req, driver, PARAMS, WINDOW, {}, batch_s=60.0, assigner=dp.hungarian)
    assert res.served == 0


def test_busy_driver_is_not_reused_before_the_trip_ends_when_two_requests_arrive_together():
    reqs = [SimRequest(rid=i, t=0.0, lat=-20.3, lon=-40.3, dlat=-20.35, dlon=-40.35, trip_s=3000.0) for i in (1, 2)]
    driver = [SimDriver(did="d", sessions=((0.0, 7200.0, -20.3, -40.3),))]
    res = simulate(reqs, driver, PARAMS, (0.0, 600.0), {}, batch_s=60.0, assigner=dp.hungarian)
    assert res.served == 1


def test_straight_line_distance_is_symmetric_and_zero_for_identical_points():
    assert reta_km(-20.3, -40.3, -20.3, -40.3) == 0.0
    assert abs(reta_km(-20.3, -40.3, -20.4, -40.2) - reta_km(-20.4, -40.2, -20.3, -40.3)) < 1e-12


def _release_world(release_s: float):
    """Um veículo ocupado até `release_s` (primeiro pedido) e um segundo pedido que chega antes da liberação."""
    first = SimRequest(rid=1, t=0.0, lat=-20.30, lon=-40.30, dlat=-20.30, dlon=-40.30, trip_s=release_s)
    second = SimRequest(rid=2, t=65.0, lat=-20.30, lon=-40.30, dlat=-20.30, dlon=-40.30, trip_s=60.0)
    drivers = [SimDriver(did="d1", sessions=((0.0, 7200.0, -20.30, -40.30),))]
    return [first, second], drivers


def test_released_vehicle_waits_for_next_lot_when_it_becomes_free_between_lots():
    # Arrange: o pedido 1 é atribuído no lote de 0 s e ocupa o veículo até 150 s; o pedido 2 espera desde 65 s
    reqs, drivers = _release_world(150.0)
    decided = []

    def spy(t, pending, candidates):
        pairs = dp.hungarian(t, pending, candidates)
        decided.extend((t, rid) for rid, _ in pairs)
        return pairs

    # Act
    simulate(reqs, drivers, PARAMS, WINDOW, {}, batch_s=60.0, assigner=spy)
    # Assert: liberado em 150 s, o veículo só é usado no lote de 180 s (não entre lotes)
    assert decided == [(0.0, 1), (180.0, 2)]


def test_released_vehicle_joins_the_lot_when_it_becomes_free_exactly_at_the_lot_instant():
    # Arrange: liberação exatamente em 120 s, instante de lote
    reqs, drivers = _release_world(120.0)
    decided = []

    def spy(t, pending, candidates):
        pairs = dp.hungarian(t, pending, candidates)
        decided.extend((t, rid) for rid, _ in pairs)
        return pairs

    # Act
    simulate(reqs, drivers, PARAMS, WINDOW, {}, batch_s=60.0, assigner=spy)
    # Assert
    assert decided == [(0.0, 1), (120.0, 2)]


def test_simulation_aborts_when_assigner_returns_an_ineligible_pair():
    # Arrange: política defeituosa que devolve um motorista inexistente
    reqs, drivers = _random_world(4)

    def broken(t, pending, candidates):
        return [(pending[0].rid, "nao_existe")] if candidates else []

    # Act / Assert
    with pytest.raises(AssertionError):
        simulate(reqs, drivers, PARAMS, WINDOW, {}, batch_s=60.0, assigner=broken)
