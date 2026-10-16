"""Simulador estendido: idêntico ao da v2 sem ganchos; lote, raio e épocas sem ocupação simultânea."""
import random

from tcc_frota.algoritmos.sim_estendido import simulate_ext
from tcc_frota.v2.sim import SimDriver, SimParams, SimRequest, simulate

P = SimParams(radius_km=4.0, speed_kmh=18.0, road_factor=1.4, patience_s=150.0)
W = (4 * 3600.0, 11 * 3600.0)


def world(seed):
    rng = random.Random(seed)
    reqs = [SimRequest(i, rng.uniform(*W), -20.3 + rng.uniform(-.05, .05), -40.3 + rng.uniform(-.05, .05),
                       -20.3 + rng.uniform(-.05, .05), -40.3 + rng.uniform(-.05, .05), rng.uniform(300, 1500),
                       rng.choice([None, 60.0, 200.0]), False, 5) for i in range(60)]
    drivers = []
    for k in range(12):
        s = rng.uniform(3 * 3600, 6 * 3600)
        commits = ((s + 3600, s + 4000, -20.3, -40.3),) if k % 4 == 0 else ()
        drivers.append(SimDriver(f"d{k}", ((s, s + 5 * 3600, -20.3 + rng.uniform(-.05, .05), -40.3 + rng.uniform(-.05, .05)),), commits))
    moves = {f"d{k}": (-20.3 + rng.uniform(-.03, .03), -40.3 + rng.uniform(-.03, .03)) for k in range(0, 12, 3)}
    return reqs, drivers, moves


def same(a, b):
    return (a.served, a.served_ids, round(a.pickup_km, 9), round(a.reposition_km, 9), a.moves_executed,
            a.move_outcomes, a.signature) == (b.served, b.served_ids, round(b.pickup_km, 9), round(b.reposition_km, 9),
                                              b.moves_executed, b.move_outcomes, b.signature)


def test_identical_to_v2_without_hooks():
    for seed in range(25):
        reqs, drivers, moves = world(seed)
        for mode in ("inicio_turno", "fim_do_dia"):
            for mv in ({}, moves):
                a = simulate(reqs, drivers, P, W, mv, max_move_km=3.0, move_mode=mode)
                b = simulate_ext(reqs, drivers, P, W, mv, max_move_km=3.0, move_mode=mode)
                assert same(a, b)


def _no_overlap(res):
    by = {}
    for did, s, e, _ in res.jobs:
        by.setdefault(did, []).append((s, e))
    for spans in by.values():
        spans.sort()
        assert all(x[1] <= y[0] + 1e-6 for x, y in zip(spans, spans[1:]))


def test_batch_dispatch_radius_and_epochs_keep_invariants():
    for seed in range(10):
        reqs, drivers, _ = world(seed)
        base = simulate(reqs, drivers, P, W)
        lote = simulate_ext(reqs, drivers, P, W, dispatch="lote", batch_s=30.0)
        small = simulate_ext(reqs, drivers, P, W, dispatch_radius_km=1.0)
        assert lote.signature == base.signature == small.signature
        epoch = simulate_ext(reqs, drivers, P, W, epochs=tuple(W[0] + 1800 * k for k in range(14)),
                             epoch_planner=lambda t, idle, busy: {d: (-20.3, -40.3) for d in idle}, max_move_km=3.0)
        for res in (lote, small, epoch):
            _no_overlap(res)
            assert res.reposition_km >= 0 and res.served <= res.n_requests
        assert epoch.reposition_km > 0


def test_mpc_epoch_plan_moves_only_idle_within_hop():
    from tcc_frota.algoritmos.mpc import epoch_times, plan_epoch
    from tcc_frota.v2.sim import reta_km
    from test_v2_policy import instance
    inp = instance(4)
    idle = {d.did: (d.lat, d.lon) for d in inp.drivers[:10]}
    busy = {d.did: (5.5 * 3600, (d.lat, d.lon)) for d in inp.drivers[10:]}
    moves = plan_epoch(4 * 3600.0, idle, busy, inp, (4, 8), horizon_h=2.0, alpha=0.05, rho_km=2.5, max_km=3.0)
    assert set(moves) <= set(idle)
    assert all(reta_km(*idle[d], *m) * inp.road_factor <= 3.0 + 1e-9 for d, m in moves.items())
    assert epoch_times((4, 6)) == (14400.0, 16200.0, 18000.0, 19800.0)
