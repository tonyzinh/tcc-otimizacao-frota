"""Alternativas ao guloso (DT001) para comparação no mesmo replay.

Todas recebem as mesmas entradas do corte D+1 e devolvem um `Plan`, para passarem pela mesma
materialização e pelo mesmo simulador. Nenhuma é política da empresa; limites e capacidades são
parâmetros experimentais (RN019).
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from datetime import datetime
from math import exp, isfinite

from tcc_frota.distance import HaversineDistance, PositionDistance, between_km
from tcc_frota.models import Position, Recommendation, Request, Vehicle, aware
from tcc_frota.optimization.greedy import Plan, _proxy
from tcc_frota.simulation.engine import SimulationConfig, simulate


def _eligible(vehicles: Sequence[Vehicle], start_at: datetime) -> dict[str, Vehicle]:
    aware(start_at)
    return {
        v.vehicle_id: v
        for v in vehicles
        if v.active and v.driver_ready and v.position is not None and v.available_from <= start_at < v.available_until
    }


def target_slots(expected_by_zone: dict[str, float], capacity_per_vehicle: float, fleet_size: int) -> dict[str, int]:
    """Vagas por zona proporcionais à demanda prevista (maior resto), no máximo uma por veículo."""
    if capacity_per_vehicle <= 0:
        raise ValueError("capacidade inválida")
    need = {z: v / capacity_per_vehicle for z, v in expected_by_zone.items() if v > 0}
    wanted = sum(need.values())
    total = min(fleet_size, int(wanted + 0.5))
    if total <= 0:
        return {}
    scale = min(1.0, total / wanted)
    quota = {z: n * scale for z, n in need.items()}
    slots = {z: int(q) for z, q in quota.items()}
    for zone in sorted(quota, key=lambda z: (-(quota[z] - slots[z]), z))[: total - sum(slots.values())]:
        slots[zone] += 1
    return {z: n for z, n in sorted(slots.items()) if n > 0}


def _plan_from_moves(
    moves: dict[str, Position],
    eligible: dict[str, Vehicle],
    zones: dict[str, Position],
    expected: dict[str, float],
    start_at: datetime,
    capacity: float,
    max_pickup_km: float,
    estimator: PositionDistance,
) -> Plan:
    """Avalia um conjunto de movimentos pelo mesmo proxy do guloso, para relatório comparável."""
    origin = {k: v.position for k, v in eligible.items() if v.position is not None}
    final = {**origin, **moves}
    base_pickup, base_cov = _proxy(origin, expected, zones, capacity, max_pickup_km, estimator)
    pickup, coverage = _proxy(final, expected, zones, capacity, max_pickup_km, estimator)
    recs = tuple(
        Recommendation(vid, origin[vid], target, start_at, between_km(estimator, origin[vid], target))
        for vid, target in sorted(moves.items())
    )
    return Plan(recs, pickup, sum(r.distance_km for r in recs), coverage, base_pickup, base_cov)


def _slot_list(slots: dict[str, int]) -> list[str]:
    return [zone for zone, count in slots.items() for _ in range(count)]


def proportional_plan(
    vehicles: list[Vehicle],
    zones: dict[str, Position],
    expected_by_zone: dict[str, float],
    start_at: datetime,
    *,
    capacity_per_vehicle: float,
    max_reposition_km: float,
    max_pickup_km: float = 15.0,
    estimator: PositionDistance | None = None,
) -> Plan:
    """Regra simples: vagas proporcionais à demanda, preenchidas pelo par veículo–vaga mais próximo."""
    estimator = estimator or HaversineDistance()
    eligible = _eligible(vehicles, start_at)
    slots = _slot_list(target_slots(expected_by_zone, capacity_per_vehicle, len(eligible)))
    pairs = sorted(
        (between_km(estimator, v.position, zones[zone]), vid, index) for vid, v in eligible.items() for index, zone in enumerate(slots)
    )
    used_vehicles: set[str] = set()
    used_slots: set[int] = set()
    moves: dict[str, Position] = {}
    for distance, vid, index in pairs:
        if vid in used_vehicles or index in used_slots or distance > max_reposition_km:
            continue
        used_vehicles.add(vid)
        used_slots.add(index)
        if distance > 1e-9:
            moves[vid] = zones[slots[index]]
    return _plan_from_moves(moves, eligible, zones, expected_by_zone, start_at, capacity_per_vehicle, max_pickup_km, estimator)


def hungarian(cost: list[list[float]]) -> list[int]:
    """Atribuição de custo mínimo (Kuhn–Munkres com potenciais), linhas <= colunas.

    Retorna, para cada linha, a coluna atribuída. Exata, O(n^2 m).
    """
    n = len(cost)
    m = len(cost[0]) if n else 0
    if n > m:
        raise ValueError("matriz precisa ter linhas <= colunas")
    inf = float("inf")
    u, v = [0.0] * (n + 1), [0.0] * (m + 1)
    p, way = [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        minv, used = [inf] * (m + 1), [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], inf, 0
            for j in range(1, m + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    result = [-1] * n
    for j in range(1, m + 1):
        if p[j]:
            result[p[j] - 1] = j - 1
    return result


def assignment_plan(
    vehicles: list[Vehicle],
    zones: dict[str, Position],
    expected_by_zone: dict[str, float],
    start_at: datetime,
    *,
    capacity_per_vehicle: float,
    max_reposition_km: float,
    max_pickup_km: float = 15.0,
    estimator: PositionDistance | None = None,
) -> Plan:
    """Método exato para a mesma meta de vagas: preenche o máximo de vagas com a menor soma de km.

    Cada veículo não usado custa uma penalidade maior que qualquer movimento permitido; assim a
    solução ótima primeiro maximiza vagas cobertas e depois minimiza o reposicionamento total.
    """
    estimator = estimator or HaversineDistance()
    eligible = _eligible(vehicles, start_at)
    ids = sorted(eligible)
    slots = _slot_list(target_slots(expected_by_zone, capacity_per_vehicle, len(ids)))
    if not ids or not slots:
        return _plan_from_moves({}, eligible, zones, expected_by_zone, start_at, capacity_per_vehicle, max_pickup_km, estimator)
    penalty = max_reposition_km + 1.0
    forbidden = penalty * (len(ids) + 1)
    cost = []
    for vid in ids:
        row = []
        for zone in slots:
            d = between_km(estimator, eligible[vid].position, zones[zone])
            row.append(d if d <= max_reposition_km else forbidden)
        row.extend([penalty] * len(ids))
        cost.append(row)
    moves = {}
    for row, column in enumerate(hungarian(cost)):
        if column < len(slots) and cost[row][column] < forbidden:
            target = zones[slots[column]]
            if between_km(estimator, eligible[ids[row]].position, target) > 1e-9:
                moves[ids[row]] = target
    return _plan_from_moves(moves, eligible, zones, expected_by_zone, start_at, capacity_per_vehicle, max_pickup_km, estimator)


def local_search_plan(
    vehicles: list[Vehicle],
    zones: dict[str, Position],
    expected_by_zone: dict[str, float],
    start_at: datetime,
    *,
    initial: Plan,
    capacity_per_vehicle: float,
    max_reposition_km: float,
    max_pickup_km: float = 15.0,
    min_coverage: float = 0.0,
    iterations: int = 1500,
    seed: int = 0,
    estimator: PositionDistance | None = None,
) -> Plan:
    """Metaheurística (simulated annealing) sobre o mesmo objetivo do guloso, partindo do guloso.

    Objetivo: pickup projetado + reposicionamento, com cobertura projetada >= a do baseline e >= min.
    Nunca devolve solução pior que a inicial nesse objetivo.
    """
    estimator = estimator or HaversineDistance()
    eligible = _eligible(vehicles, start_at)
    origin = {k: v.position for k, v in eligible.items() if v.position is not None}
    if not origin or not expected_by_zone:
        return initial
    _, base_cov = _proxy(origin, expected_by_zone, zones, capacity_per_vehicle, max_pickup_km, estimator)

    def value(moves: dict[str, Position]) -> float:
        final = {**origin, **moves}
        pickup, coverage = _proxy(final, expected_by_zone, zones, capacity_per_vehicle, max_pickup_km, estimator)
        if coverage is None or coverage + 1e-9 < max(min_coverage, base_cov or 0.0):
            return float("inf")
        return pickup + sum(between_km(estimator, origin[k], p) for k, p in moves.items())

    rng = random.Random(seed)
    zone_ids = sorted(zones)
    vehicle_ids = sorted(origin)
    current = {r.vehicle_id: r.destination for r in initial.recommendations if r.vehicle_id in origin}
    current_value = value(current)
    best, best_value = dict(current), current_value
    temperature = 1.0
    cooling = (0.01 / temperature) ** (1 / max(iterations, 1))
    for _ in range(iterations):
        vid = rng.choice(vehicle_ids)
        candidate = dict(current)
        choice = rng.choice(zone_ids + ["ficar"])
        if choice == "ficar":
            candidate.pop(vid, None)
        else:
            distance = between_km(estimator, origin[vid], zones[choice])
            if distance > max_reposition_km or distance < 1e-9:
                continue
            candidate[vid] = zones[choice]
        candidate_value = value(candidate)
        if not isfinite(candidate_value):
            continue
        if candidate_value <= current_value or rng.random() < exp((current_value - candidate_value) / temperature):
            current, current_value = candidate, candidate_value
            if current_value < best_value - 1e-9:
                best, best_value = dict(current), current_value
        temperature *= cooling
    if best_value >= value({r.vehicle_id: r.destination for r in initial.recommendations}) - 1e-9:
        return initial
    return _plan_from_moves(best, eligible, zones, expected_by_zone, start_at, capacity_per_vehicle, max_pickup_km, estimator)


def simulated_greedy_plan(
    vehicles: list[Vehicle],
    zones: dict[str, Position],
    expected_by_zone: dict[str, float],
    start_at: datetime,
    *,
    scenarios: Sequence[Sequence[Request]],
    sim_config: SimulationConfig,
    max_reposition_km: float,
    candidate_zones: int = 8,
    max_moves: int = 10,
    estimator: PositionDistance | None = None,
) -> Plan:
    """Guloso cujo objetivo é o KM vazio **simulado** em dias históricos de treino.

    Cada cenário é um dia anterior ao corte, com seus pedidos reais deslocados para D+1 e a frota
    prevista. Aceita o movimento que mais reduz a média de pickup + reposicionamento sem reduzir a
    cobertura média. Usa somente informação disponível no corte (RN020).
    """
    estimator = estimator or HaversineDistance()
    eligible = _eligible(vehicles, start_at)
    fleet = [v for v in vehicles if v.vehicle_id in eligible]
    if not fleet or not scenarios:
        return Plan((), 0.0, 0.0, None, 0.0, None)
    targets = [z for z, _ in sorted(expected_by_zone.items(), key=lambda kv: (-kv[1], kv[0]))[:candidate_zones]]

    def evaluate(recs: tuple[Recommendation, ...]) -> tuple[float, float, float]:
        km = pickup = served = total = 0.0
        for requests in scenarios:
            result = simulate("cenario_treino", list(requests), fleet, sim_config, recommendations=recs, estimator=estimator)
            km += result.km_dead_estimated
            pickup += result.pickup_km
            served += len(result.served_ids)
            total += len(result.request_ids)
        n = len(scenarios)
        return km / n, pickup / n, (served / total if total else 1.0)

    chosen: tuple[Recommendation, ...] = ()
    base_km, base_pickup, base_cov = evaluate(chosen)
    current_km = base_km
    moved: set[str] = set()
    for _ in range(max_moves):
        best: tuple[float, Recommendation, float, float] | None = None
        for vehicle in sorted(fleet, key=lambda v: v.vehicle_id):
            if vehicle.vehicle_id in moved:
                continue
            for zone in targets:
                distance = between_km(estimator, vehicle.position, zones[zone])
                if distance < 1e-9 or distance > max_reposition_km:
                    continue
                rec = Recommendation(vehicle.vehicle_id, vehicle.position, zones[zone], start_at, distance)
                km, pickup, coverage = evaluate(chosen + (rec,))
                if coverage + 1e-9 < base_cov:
                    continue
                gain = current_km - km
                if gain > 1e-6 and (best is None or gain > best[0] + 1e-9):
                    best = (gain, rec, km, pickup)
        if best is None:
            break
        _, rec, current_km, _ = best
        chosen += (rec,)
        moved.add(rec.vehicle_id)
    _, final_pickup, final_cov = evaluate(chosen)
    return Plan(
        chosen,
        final_pickup,
        sum(r.distance_km for r in chosen),
        final_cov,
        base_pickup,
        base_cov,
        objective="mean simulated estimated dead km over training days; coverage not below baseline",
    )
