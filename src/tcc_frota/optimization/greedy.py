"""Guloso determinístico: melhora proxy de pickup + custo de reposição.

Cada veículo oferece `capacity_per_vehicle` atendimentos estimados na faixa. Isso
é uma aproximação acadêmica, não uma regra operacional da empresa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite

from tcc_frota.distance import HaversineDistance, PositionDistance, between_km
from tcc_frota.models import Commitment, Position, Recommendation, Vehicle, aware


@dataclass(frozen=True)
class Plan:
    recommendations: tuple[Recommendation, ...]
    projected_pickup_km: float
    reposition_km: float
    projected_coverage: float | None
    baseline_projected_pickup_km: float
    baseline_projected_coverage: float | None
    objective: str = "estimated_pickup_km + estimated_reposition_km; coverage constrained"


def _proxy(
    locations: dict[str, Position],
    demand: dict[str, float],
    zones: dict[str, Position],
    capacity: float,
    max_pickup_km: float,
    estimator: PositionDistance,
) -> tuple[float, float | None]:
    total = sum(demand.values())
    if total <= 0:
        return 0.0, None
    remaining = dict.fromkeys(locations, capacity)
    pickup = covered = 0.0
    for zone_id in sorted(demand):
        need = demand[zone_id]
        candidates = sorted(
            ((between_km(estimator, pos, zones[zone_id]), vehicle_id) for vehicle_id, pos in locations.items()),
            key=lambda item: (item[0], item[1]),
        )
        for distance, vehicle_id in candidates:
            if need <= 1e-12 or distance > max_pickup_km:
                break
            qty = min(need, remaining[vehicle_id])
            pickup += qty * distance
            covered += qty
            remaining[vehicle_id] -= qty
            need -= qty
    return pickup, covered / total


def greedy_plan(
    vehicles: list[Vehicle],
    zones: dict[str, Position],
    expected_by_zone: dict[str, float],
    start_at: datetime,
    *,
    commitments: tuple[Commitment, ...] = (),
    capacity_per_vehicle: float = 2.0,
    min_coverage: float = 0.0,
    max_pickup_km: float = 15.0,
    max_reposition_km: float = 15.0,
    speed_kmh: float = 30.0,
    max_moves: int | None = None,
    estimator: PositionDistance | None = None,
) -> Plan:
    aware(start_at)
    estimator = estimator or HaversineDistance()
    if capacity_per_vehicle <= 0 or speed_kmh <= 0 or not 0 <= min_coverage <= 1:
        raise ValueError("parâmetros do plano inválidos")
    if max_pickup_km < 0 or max_reposition_km < 0:
        raise ValueError("distâncias máximas inválidas")
    if any(zone not in zones or value < 0 or not isfinite(value) for zone, value in expected_by_zone.items()):
        raise ValueError("previsão inválida")
    eligible = {
        v.vehicle_id: v
        for v in vehicles
        if v.active
        and v.driver_ready
        and v.position is not None
        and v.available_from <= start_at < v.available_until
        and not any(c.vehicle_id == v.vehicle_id and c.start <= start_at < c.end for c in commitments)
    }
    positions = {key: v.position for key, v in eligible.items() if v.position is not None}
    base_pickup, base_coverage = _proxy(positions, expected_by_zone, zones, capacity_per_vehicle, max_pickup_km, estimator)
    if not positions or not expected_by_zone or sum(expected_by_zone.values()) <= 0:
        return Plan((), base_pickup, 0.0, base_coverage, base_pickup, base_coverage)
    selected: list[Recommendation] = []
    current_pickup, current_coverage = base_pickup, base_coverage
    reposition = 0.0
    used: set[str] = set()
    limit = len(positions) if max_moves is None else max_moves
    for _ in range(limit):
        best: tuple[float, str, str, float, float, float] | None = None
        for vehicle_id in sorted(positions):
            if vehicle_id in used:
                continue
            vehicle = eligible[vehicle_id]
            for zone_id in sorted(zones):
                target = zones[zone_id]
                distance = between_km(estimator, positions[vehicle_id], target)
                if distance < 1e-9 or distance > max_reposition_km:
                    continue
                finish = start_at + timedelta(hours=distance / speed_kmh)
                if finish > vehicle.available_until or any(
                    c.vehicle_id == vehicle_id and c.start < finish and c.end > start_at for c in commitments
                ):
                    continue
                trial = dict(positions)
                trial[vehicle_id] = target
                pickup, coverage = _proxy(trial, expected_by_zone, zones, capacity_per_vehicle, max_pickup_km, estimator)
                if coverage is None or coverage + 1e-9 < min_coverage:
                    continue
                if base_coverage is not None and coverage + 1e-9 < base_coverage:
                    continue
                improvement = (current_pickup + reposition) - (pickup + reposition + distance)
                candidate = (improvement, vehicle_id, zone_id, distance, pickup, coverage)
                if improvement > 1e-9 and (
                    best is None
                    or improvement > best[0] + 1e-9
                    or (abs(improvement - best[0]) <= 1e-9 and (vehicle_id, zone_id) < (best[1], best[2]))
                ):
                    best = candidate
        if best is None:
            break
        _, vehicle_id, zone_id, distance, current_pickup, current_coverage = best
        selected.append(Recommendation(vehicle_id, positions[vehicle_id], zones[zone_id], start_at, distance))
        positions[vehicle_id] = zones[zone_id]
        reposition += distance
        used.add(vehicle_id)
    return Plan(tuple(selected), current_pickup, reposition, current_coverage, base_pickup, base_coverage)
