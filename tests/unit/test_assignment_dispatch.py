"""Testes da atribuição em lote (mais próximo FIFO e Húngaro). Padrão Arrange–Act–Assert."""

from __future__ import annotations

import itertools
from types import SimpleNamespace

import numpy as np
import pytest

from tcc_frota.assignment import dispatch as dp
from tcc_frota.domain.entities import SimDriver, SimParams, SimRequest
from tcc_frota.simulation.engine import simulate


def _requests(n):
    return [SimpleNamespace(rid=f"r{i}") for i in range(n)]


def _candidates(costs):
    """costs[i][j] em km (None = inelegível) -> {rid: [(km, did)]} ordenado por distância."""
    out = {}
    for i, row in enumerate(costs):
        pairs = sorted((c, f"d{j}") for j, c in enumerate(row) if c is not None)
        if pairs:
            out[f"r{i}"] = pairs
    return out


def _brute_force_optimum(costs):
    """(máx. de pares, custo mínimo com esse máximo) por enumeração de todas as atribuições parciais."""
    n, m = len(costs), len(costs[0]) if costs else 0
    best = (0, 0.0)
    for k in range(min(n, m), -1, -1):
        found = None
        for rows in itertools.combinations(range(n), k):
            for cols in itertools.permutations(range(m), k):
                cs = [costs[r][c] for r, c in zip(rows, cols, strict=True)]
                if all(c is not None for c in cs):
                    found = sum(cs) if found is None else min(found, sum(cs))
        if found is not None:
            return k, found
    return best


def _cost_of(pairs, costs):
    return sum(costs[int(r[1:])][int(d[1:])] for r, d in pairs)


def test_hungarian_returns_empty_when_lot_has_no_requests():
    assert dp.hungarian(0.0, [], {}) == []


def test_hungarian_returns_empty_when_no_vehicle_is_eligible():
    assert dp.hungarian(0.0, _requests(2), {}) == []


def test_nearest_fifo_returns_empty_when_no_vehicle_is_eligible():
    assert dp.nearest_fifo(0.0, _requests(2), {}) == []


def test_hungarian_assigns_each_vehicle_once_when_rectangular_matrix_has_more_requests_than_vehicles():
    costs = [[1.0, 2.0], [2.0, 1.0], [1.5, 1.5]]
    pairs = dp.hungarian(0.0, _requests(3), _candidates(costs))
    assert len(pairs) == 2
    assert len({d for _r, d in pairs}) == 2 and len({r for r, _d in pairs}) == 2


def test_hungarian_assigns_every_request_when_rectangular_matrix_has_more_vehicles_than_requests():
    costs = [[5.0, 1.0, 9.0], [4.0, 2.0, 8.0]]
    pairs = dp.hungarian(0.0, _requests(2), _candidates(costs))
    assert len(pairs) == 2
    assert _cost_of(pairs, costs) == pytest.approx(_brute_force_optimum(costs)[1])


def test_hungarian_skips_infeasible_pairs_when_request_has_no_eligible_vehicle():
    costs = [[None, None], [1.0, 2.0]]
    pairs = dp.hungarian(0.0, _requests(2), _candidates(costs))
    assert pairs == [("r1", "d0")]


def test_hungarian_serves_more_requests_than_sequential_greedy_when_nearest_choice_blocks_a_request():
    # P0 prefere V0 (2 km) mas P1 só tem V0 elegível; o sequencial deixa P1 sem veículo.
    costs = [[2.0, 3.0], [1.0, None]]
    cands = _candidates(costs)
    greedy = dp.nearest_fifo(0.0, _requests(2), cands)
    joint = dp.hungarian(0.0, _requests(2), cands)
    assert len(greedy) == 1
    assert len(joint) == 2


def test_hungarian_prioritises_attendance_over_total_distance_when_both_conflict():
    # atender dois pedidos custa 100 km; atender só um custaria 1 km. Atendimento tem prioridade lexicográfica.
    costs = [[1.0, 50.0], [None, 50.0]]
    pairs = dp.hungarian(0.0, _requests(2), _candidates(costs))
    assert len(pairs) == 2


def test_hungarian_breaks_ties_deterministically_when_costs_are_equal():
    costs = [[1.0, 1.0], [1.0, 1.0]]
    first = dp.hungarian(0.0, _requests(2), _candidates(costs))
    second = dp.hungarian(0.0, _requests(2), _candidates(costs))
    assert first == second


@pytest.mark.parametrize("seed", range(30))
def test_hungarian_matches_brute_force_optimum_when_instance_is_small(seed):
    rng = np.random.default_rng(seed)
    n, m = int(rng.integers(1, 5)), int(rng.integers(1, 5))
    costs = [[None if rng.random() < 0.3 else round(float(rng.uniform(0.1, 9)), 2) for _ in range(m)] for _ in range(n)]
    pairs = dp.hungarian(0.0, _requests(n), _candidates(costs))
    best_n, best_cost = _brute_force_optimum(costs)
    assert len(pairs) == best_n
    assert _cost_of(pairs, costs) == pytest.approx(best_cost, abs=1e-2 * max(best_n, 1))


@pytest.mark.parametrize("seed", range(20))
def test_hungarian_matches_scipy_oracle_when_instance_is_larger(seed):
    scipy_opt = pytest.importorskip("scipy.optimize")
    rng = np.random.default_rng(100 + seed)
    n, m = int(rng.integers(5, 15)), int(rng.integers(5, 15))
    costs = [[None if rng.random() < 0.4 else round(float(rng.uniform(0.1, 9)), 3) for _ in range(m)] for _ in range(n)]
    pairs = dp.hungarian(0.0, _requests(n), _candidates(costs))
    big = 1e6
    mat = np.array([[c if c is not None else 0.0 for c in row] for row in costs])
    feasible = np.array([[c is not None for c in row] for row in costs])
    aug = np.where(feasible, mat - big, 0.0)
    r, c = scipy_opt.linear_sum_assignment(aug)
    ref = [(i, j) for i, j in zip(r, c, strict=True) if feasible[i, j]]
    assert len(pairs) == len(ref)
    assert _cost_of(pairs, costs) == pytest.approx(sum(mat[i, j] for i, j in ref), abs=5e-3 * max(len(ref), 1))


def test_kuhn_munkres_returns_optimal_columns_when_square_matrix_is_given():
    a = np.array([[2.0, 3.0, 9.0], [1.0, 8.0, 7.0], [6.0, 4.0, 5.0]])
    cols = dp.kuhn_munkres(a)
    assert sum(a[i, j] for i, j in enumerate(cols)) == pytest.approx(9.0)


# ---------- integração com o simulador ----------
PARAMS = SimParams(radius_km=4.5, speed_kmh=30.0, road_factor=1.0, patience_s=180.0)


def _world():
    # pedidos próximos de dois motoristas em linha reta (graus -> ~km)
    reqs = [SimRequest(rid=1, t=0.0, lat=-20.3, lon=-40.3, dlat=-20.31, dlon=-40.31, trip_s=600.0)]
    drivers = [SimDriver(did="d1", sessions=((0.0, 86400.0, -20.301, -40.3),))]
    return reqs, drivers


def test_batch_wait_includes_time_until_lot_boundary_when_request_arrives_inside_lot():
    reqs = [SimRequest(rid=1, t=10.0, lat=-20.3, lon=-40.3, dlat=-20.31, dlon=-40.31, trip_s=600.0)]
    drivers = [SimDriver(did="d1", sessions=((0.0, 86400.0, -20.3, -40.3),))]
    res = simulate(reqs, drivers, PARAMS, (0.0, 3600.0), {}, batch_s=60.0, assigner=dp.POLICIES["hungarian"])
    assert res.served == 1
    assert res.wait_s[0] >= 50.0 - 1e-6  # chegou em 10 s; só é decidido no lote de 60 s


def test_batch_wait_equals_lot_delay_plus_approach_travel_when_driver_is_away_from_origin():
    # chegada em 10 s, decisão no lote de 60 s (50 s de atraso), motorista a ~1,1 km (30 km/h, fator 1): espera = atraso + deslocamento
    reqs = [SimRequest(rid=1, t=10.0, lat=-20.30, lon=-40.30, dlat=-20.31, dlon=-40.31, trip_s=600.0)]
    drivers = [SimDriver(did="d1", sessions=((0.0, 86400.0, -20.31, -40.30),))]
    res = simulate(reqs, drivers, PARAMS, (0.0, 3600.0), {}, batch_s=60.0, assigner=dp.POLICIES["hungarian"])
    approach_s = res.pickup_km / PARAMS.speed_kmh * 3600.0
    assert res.served == 1 and res.pickup_km > 0
    assert res.wait_s[0] == pytest.approx(50.0 + approach_s, abs=1e-6)


def test_request_is_not_served_twice_when_two_policies_share_the_same_inputs():
    reqs, drivers = _world()
    a = simulate(reqs, drivers, PARAMS, (0.0, 3600.0), {})
    c = simulate(reqs, drivers, PARAMS, (0.0, 3600.0), {}, batch_s=60.0, assigner=dp.POLICIES["hungarian"])
    assert a.signature == c.signature
    assert a.served <= len(reqs) and c.served <= len(reqs)


def test_simulation_returns_zero_served_when_there_are_no_vehicles():
    reqs, _ = _world()
    res = simulate(reqs, [], PARAMS, (0.0, 3600.0), {}, batch_s=60.0, assigner=dp.POLICIES["hungarian"])
    assert res.served == 0 and res.empty_km == 0.0


def test_didactic_fixture_shows_joint_assignment_cheaper_than_sequential_when_nearest_choice_blocks_a_vehicle():
    import json
    from pathlib import Path

    fx = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "didactic_lot_3x3.json").read_text(encoding="utf-8"))
    costs = fx["custos_km"]
    cands = _candidates(costs)
    sequential = dp.nearest_fifo(0.0, _requests(3), cands)
    joint = dp.hungarian(0.0, _requests(3), cands)
    assert _cost_of(sequential, costs) == fx["custo_sequencial_km"]
    assert _cost_of(joint, costs) == fx["custo_otimo_km"] == _brute_force_optimum(costs)[1]


def _timed_requests(n):
    return [SimpleNamespace(rid=f"r{i}", t=float(i)) for i in range(n)]


def test_global_greedy_takes_the_smallest_eligible_pair_first_when_pairs_compete():
    # Arrange: r0-d0 = 2 km, r1-d0 = 1 km (menor par); r0-d1 = 3 km
    reqs, cands = _timed_requests(2), _candidates([[2.0, 3.0], [1.0, None]])
    # Act
    pairs = dp.global_greedy(0.0, reqs, cands)
    # Assert
    assert sorted(pairs) == [("r0", "d1"), ("r1", "d0")]


def test_global_greedy_can_serve_fewer_requests_than_hungarian_when_smallest_pair_blocks_another_request():
    # Arrange: r0 só alcança d0 (2 km); r1 alcança d0 (1 km) e d1 (5 km). O menor par (r1-d0) tira de r0 o único veículo.
    reqs, cands = _timed_requests(2), _candidates([[2.0, None], [1.0, 5.0]])
    cands_block = _candidates([[2.0], [1.0]])
    # Act
    greedy = dp.global_greedy(0.0, reqs, cands_block)
    hung = dp.hungarian(0.0, reqs, cands)
    greedy_full = dp.global_greedy(0.0, reqs, cands)
    # Assert: com um só veículo, ambos servem 1; com d1 disponível, o guloso pega r1-d0 e deixa r0 sem par, o Húngaro serve os dois
    assert len(greedy) == 1
    assert len(hung) == 2
    assert greedy_full == [("r1", "d0")]


def test_global_greedy_breaks_distance_ties_by_request_arrival_when_costs_are_equal():
    # Arrange: dois pedidos à mesma distância do único veículo
    reqs, cands = _timed_requests(2), _candidates([[1.0], [1.0]])
    # Act
    pairs = dp.global_greedy(0.0, reqs, cands)
    # Assert: o pedido que chegou antes vence o empate
    assert pairs == [("r0", "d0")]
