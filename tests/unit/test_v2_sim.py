"""Simulador v2 (Fase 4): fila, raio, ocupação, KM de reposicionamento e entradas idênticas."""

import random

import pytest

from tcc_frota.v2.sim import SimDriver, SimParams, SimRequest, reta_km, simulate

P = SimParams(radius_km=5.0, speed_kmh=18.0, road_factor=1.4, patience_s=120.0)
W = (4 * 3600.0, 11 * 3600.0)
LAT, LON = -20.30, -40.30


def r(rid, t, lat=LAT, lon=LON, trip=600.0, patience=None):
    return SimRequest(rid, t, lat, lon, lat + 0.02, lon, trip, patience, False, int(t // 3600))


def d(did, start=4 * 3600.0, end=12 * 3600.0, lat=LAT, lon=LON, commits=()):
    return SimDriver(did, ((start, end, lat, lon),), tuple(commits))


def test_nearest_free_driver_within_radius():
    res = simulate([r(1, 5 * 3600)], [d("perto", lat=LAT + 0.01), d("longe", lat=LAT + 0.2)], P, W)
    assert res.served == 1
    assert res.pickup_km == pytest.approx(reta_km(LAT + 0.01, LON, LAT, LON) * 1.4)


def test_driver_beyond_radius_is_never_dispatched():
    res = simulate([r(1, 5 * 3600)], [d("longe", lat=LAT + 0.2)], P, W)
    assert res.served == 0


def test_queue_serves_within_patience_and_expires_after():
    busy = [r(1, 5 * 3600, trip=60.0)]
    ok = simulate(busy + [r(2, 5 * 3600 + 30)], [d("a")], P, W)
    assert ok.served == 2 and max(ok.wait_s) >= 30
    late = simulate([r(1, 5 * 3600, trip=1000.0), r(2, 5 * 3600 + 30)], [d("a")], P, W)
    assert late.served == 1
    impatient = simulate([r(1, 5 * 3600, trip=60.0), r(2, 5 * 3600 + 30, patience=5.0)], [d("a")], P, W)
    assert impatient.served == 1


def test_commitment_blocks_overlapping_dispatch():
    commit = [(5 * 3600 + 300, 6 * 3600, LAT, LON)]
    res = simulate([r(1, 5 * 3600, trip=1200.0)], [d("a", commits=commit)], P, W)
    assert res.served == 0


def _no_overlap(res):
    by = {}
    for did, s, e, _ in res.jobs:
        by.setdefault(did, []).append((s, e))
    for spans in by.values():
        spans.sort()
        assert all(a[1] <= b[0] + 1e-6 for a, b in zip(spans, spans[1:]))


def test_no_driver_serves_two_jobs_at_once_random_instances():
    rng = random.Random(7)
    for _ in range(20):
        drivers = []
        for k in range(6):
            cs = []
            if rng.random() < 0.5:
                s = rng.uniform(4, 10) * 3600
                cs.append((s, s + rng.uniform(600, 3600), LAT + rng.uniform(-0.05, 0.05), LON))
            drivers.append(
                d(
                    f"d{k}",
                    start=rng.uniform(3, 6) * 3600,
                    lat=LAT + rng.uniform(-0.05, 0.05),
                    lon=LON + rng.uniform(-0.05, 0.05),
                    commits=cs,
                )
            )
        reqs = [
            r(i, rng.uniform(4, 11) * 3600, LAT + rng.uniform(-0.05, 0.05), LON + rng.uniform(-0.05, 0.05), trip=rng.uniform(300, 1800))
            for i in range(60)
        ]
        moves = {f"d{k}": (LAT + 0.01, LON) for k in range(0, 6, 2)}
        res = simulate(reqs, drivers, P, W, moves)
        _no_overlap(res)


def test_reposition_km_counted_and_signature_unchanged_by_plan():
    reqs = [r(1, 6 * 3600)]
    drivers = [d("a", lat=LAT + 0.03)]
    base = simulate(reqs, drivers, P, W)
    prop = simulate(reqs, drivers, P, W, {"a": (LAT, LON)})
    assert base.signature == prop.signature
    assert prop.moves_executed == 1
    assert prop.reposition_km == pytest.approx(reta_km(LAT + 0.03, LON, LAT, LON) * 1.4)
    assert prop.empty_km == pytest.approx(prop.pickup_km + prop.reposition_km)
    assert prop.pickup_km < base.pickup_km


def test_moves_respect_cap_unknown_driver_and_first_availability():
    reqs = [r(1, 6 * 3600)]
    far = simulate(reqs, [d("a", lat=LAT + 0.1)], P, W, {"a": (LAT, LON)}, max_move_km=3.0)
    assert far.moves_executed == 0 and far.reposition_km == 0
    ghost = simulate(reqs, [d("a")], P, W, {"fantasma": (LAT, LON)})
    assert ghost.moves_planned == 1 and ghost.moves_executed == 0
    commit = [(3 * 3600, 5 * 3600, LAT + 0.02, LON)]
    busy = simulate(reqs, [d("a", start=3 * 3600, commits=commit)], P, W, {"a": (LAT, LON)})
    assert busy.moves_executed == 0


def test_deterministic():
    reqs = [r(i, 4 * 3600 + 97 * i, LAT + 0.001 * i) for i in range(30)]
    drivers = [d(f"d{k}", lat=LAT + 0.004 * k) for k in range(5)]
    a = simulate(reqs, drivers, P, W, {"d1": (LAT, LON)})
    b = simulate(reqs, drivers, P, W, {"d1": (LAT, LON)})
    assert (a.served, a.pickup_km, a.reposition_km, a.wait_s) == (b.served, b.pickup_km, b.reposition_km, b.wait_s)


def test_end_of_day_mode_starts_session_at_target_and_counts_km_from_last_position():
    reqs = [r(1, 6 * 3600)]
    drivers = [d("a", start=5 * 3600, lat=LAT + 0.03)]
    origin = (LAT + 0.02, LON)
    res = simulate(reqs, drivers, P, W, {"a": (LAT, LON)}, move_mode="fim_do_dia", move_origins={"a": origin})
    assert res.moves_executed == 1
    assert res.reposition_km == pytest.approx(reta_km(*origin, LAT, LON) * 1.4)
    assert res.pickup_km == pytest.approx(0.0, abs=1e-9)  # começou o dia na zona-alvo
    early = simulate(
        reqs, [d("a", start=2 * 3600, lat=LAT + 0.03)], P, W, {"a": (LAT, LON)}, move_mode="fim_do_dia", move_origins={"a": origin}
    )
    assert early.moves_executed == 0  # já trabalhava antes da janela
    capped = simulate(reqs, drivers, P, W, {"a": (LAT, LON)}, move_mode="fim_do_dia", move_origins={"a": (LAT + 0.2, LON)}, max_move_km=5.0)
    assert capped.moves_executed == 0


def test_trace_does_not_change_results_and_records_move_outcomes():
    reqs = [r(1, 6 * 3600), r(2, 6 * 3600 + 60, LAT + 0.3)]
    drivers = [d("a", lat=LAT + 0.03), d("b", lat=LAT + 0.2)]
    moves = {"a": (LAT, LON), "b": (LAT, LON), "fantasma": (LAT, LON)}
    plain = simulate(reqs, drivers, P, W, moves, max_move_km=6.0)
    trace: list = []
    traced = simulate(reqs, drivers, P, W, moves, max_move_km=6.0, trace=trace)
    assert (plain.served, plain.pickup_km, plain.reposition_km, plain.wait_s) == (
        traced.served,
        traced.pickup_km,
        traced.reposition_km,
        traced.wait_s,
    )
    assert traced.move_outcomes == {"a": "executed", "b": "limit", "fantasma": "absent"}
    kinds = [e[1] for e in trace]
    assert kinds.count("request_created") == 2 and kinds.count("request_unserved") == 1
    assert kinds.count("dispatch") == kinds.count("pickup") == kinds.count("dropoff") == 1
    assert kinds.count("reposition_start") == kinds.count("reposition_end") == 1
