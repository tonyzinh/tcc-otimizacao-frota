"""Replay cronológico sintético, sem informação futura no plano D+1."""

from __future__ import annotations

import hashlib
import heapq
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

from tcc_frota.distance import HaversineDistance, PositionDistance, between_km
from tcc_frota.models import (
    Commitment,
    Event,
    Position,
    Recommendation,
    Request,
    ScenarioResult,
    Vehicle,
    VehicleState,
    aware,
)


@dataclass(frozen=True)
class SimulationConfig:
    start_at: datetime
    end_at: datetime
    speed_kmh: float = 30.0
    max_pickup_minutes: float = 18.0

    def __post_init__(self) -> None:
        aware(self.start_at)
        aware(self.end_at)
        if self.end_at <= self.start_at or self.speed_kmh <= 0 or self.max_pickup_minutes < 0:
            raise ValueError("configuração temporal inválida")


def _signature(requests: list[Request], vehicles: list[Vehicle], commitments: tuple[Commitment, ...], config: SimulationConfig) -> str:
    payload = json.dumps(
        {
            "requests": [asdict(item) for item in sorted(requests, key=lambda r: r.request_id)],
            "vehicles": [asdict(item) for item in sorted(vehicles, key=lambda v: v.vehicle_id)],
            "commitments": [asdict(item) for item in sorted(commitments, key=lambda c: (c.vehicle_id, c.start))],
            "config": asdict(config),
        },
        default=str,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def simulate(
    name: str,
    requests: list[Request],
    vehicles: list[Vehicle],
    config: SimulationConfig,
    *,
    commitments: tuple[Commitment, ...] = (),
    recommendations: tuple[Recommendation, ...] = (),
    estimator: PositionDistance | None = None,
) -> ScenarioResult:
    estimator = estimator or HaversineDistance()
    if len({r.request_id for r in requests}) != len(requests):
        raise ValueError("solicitações duplicadas")
    if len({v.vehicle_id for v in vehicles}) != len(vehicles):
        raise ValueError("veículos duplicados")
    by_vehicle = {v.vehicle_id: v for v in vehicles}
    for commitment in commitments:
        if commitment.vehicle_id not in by_vehicle:
            raise ValueError("compromisso de veículo desconhecido")
    for vehicle_id in by_vehicle:
        intervals = sorted((c.start, c.end) for c in commitments if c.vehicle_id == vehicle_id)
        if any(previous[1] > following[0] for previous, following in zip(intervals, intervals[1:])):
            raise ValueError("compromissos externos sobrepostos")
    result = ScenarioResult(
        name,
        tuple(sorted(r.request_id for r in requests if config.start_at <= r.created_at < config.end_at)),
        tuple(sorted(by_vehicle)),
        input_signature=_signature(requests, vehicles, commitments, config),
        distance_method=estimator.name,
    )
    states = {v.vehicle_id: VehicleState.INDISPONIVEL for v in vehicles}
    positions: dict[str, Position | None] = {v.vehicle_id: v.position for v in vehicles}
    active_commitments: set[str] = set()
    queue: list[tuple[datetime, int, int, str, object]] = []
    seq = 0

    def push(at: datetime, priority: int, kind: str, payload: object) -> None:
        nonlocal seq
        seq += 1
        heapq.heappush(queue, (at, priority, seq, kind, payload))

    for vehicle in vehicles:
        if vehicle.available_from < config.end_at:
            push(max(vehicle.available_from, config.start_at), 0, "availability_start", vehicle.vehicle_id)
            push(vehicle.available_until, 0, "availability_end", vehicle.vehicle_id)
    for commitment in commitments:
        if commitment.end > config.start_at:
            push(max(commitment.start, config.start_at), 1, "commitment_start", commitment)
            push(commitment.end, 0, "commitment_end", commitment)
    for request in sorted(requests, key=lambda r: (r.created_at, r.request_id)):
        if config.start_at <= request.created_at < config.end_at:
            push(request.created_at, 3, "request", request)
    for recommendation in recommendations:
        if recommendation.vehicle_id not in by_vehicle:
            raise ValueError("recomendação de veículo desconhecido")
        if recommendation.start_at < config.start_at or recommendation.start_at >= config.end_at:
            raise ValueError("recomendação fora do horizonte")
        push(recommendation.start_at, 2, "reposition_start", recommendation)

    while queue:
        at, _, _, kind, item = heapq.heappop(queue)
        if kind == "availability_start":
            vehicle_id = str(item)
            vehicle = by_vehicle[vehicle_id]
            if vehicle.active and vehicle.driver_ready and positions[vehicle_id] is not None and vehicle_id not in active_commitments:
                states[vehicle_id] = VehicleState.LIVRE
            result.events.append(Event(at, kind, vehicle_id))
        elif kind == "availability_end":
            vehicle_id = str(item)
            if states[vehicle_id] not in {VehicleState.LIVRE, VehicleState.INDISPONIVEL}:
                raise ValueError("veículo ocupado após fim da disponibilidade")
            states[vehicle_id] = VehicleState.INDISPONIVEL
            result.events.append(Event(at, kind, vehicle_id))
        elif kind == "commitment_start":
            commitment = item
            assert isinstance(commitment, Commitment)
            vehicle_id = commitment.vehicle_id
            if states[vehicle_id] not in {VehicleState.LIVRE, VehicleState.INDISPONIVEL}:
                raise ValueError("compromisso externo sobrepõe viagem ou reposicionamento")
            active_commitments.add(vehicle_id)
            states[vehicle_id] = VehicleState.INDISPONIVEL
            result.events.append(Event(at, kind, vehicle_id))
        elif kind == "commitment_end":
            commitment = item
            assert isinstance(commitment, Commitment)
            vehicle_id = commitment.vehicle_id
            active_commitments.discard(vehicle_id)
            positions[vehicle_id] = commitment.end_position
            vehicle = by_vehicle[vehicle_id]
            states[vehicle_id] = (
                VehicleState.LIVRE
                if (
                    vehicle.active
                    and vehicle.driver_ready
                    and positions[vehicle_id] is not None
                    and vehicle.available_from <= at < vehicle.available_until
                )
                else VehicleState.INDISPONIVEL
            )
            result.events.append(Event(at, kind, vehicle_id))
        elif kind == "reposition_start":
            recommendation = item
            assert isinstance(recommendation, Recommendation)
            vehicle_id = recommendation.vehicle_id
            if states[vehicle_id] != VehicleState.LIVRE or positions[vehicle_id] != recommendation.origin:
                raise ValueError("reposição inviável no replay")
            actual_km = between_km(estimator, recommendation.origin, recommendation.destination)
            if abs(actual_km - recommendation.distance_km) > 1e-6:
                raise ValueError("distância da recomendação difere do estimador")
            finish = at + timedelta(hours=actual_km / config.speed_kmh)
            if finish > by_vehicle[vehicle_id].available_until or any(
                c.vehicle_id == vehicle_id and c.start < finish and c.end > at for c in commitments
            ):
                raise ValueError("reposição conflita com disponibilidade")
            states[vehicle_id] = VehicleState.REPOSICIONANDO
            result.reposition_km += actual_km
            push(finish, 0, "reposition_end", recommendation)
            result.events.append(Event(at, kind, vehicle_id))
        elif kind == "reposition_end":
            recommendation = item
            assert isinstance(recommendation, Recommendation)
            positions[recommendation.vehicle_id] = recommendation.destination
            states[recommendation.vehicle_id] = VehicleState.LIVRE
            result.events.append(Event(at, kind, recommendation.vehicle_id))
        elif kind == "pickup_arrival":
            request, vehicle_id = item
            assert isinstance(request, Request)
            states[vehicle_id] = VehicleState.EM_VIAGEM
            result.events.append(Event(at, "pickup_arrival", vehicle_id, request.request_id))
            result.events.append(Event(at, "trip_start", vehicle_id, request.request_id))
        elif kind == "trip_end":
            request, vehicle_id = item
            assert isinstance(request, Request)
            positions[vehicle_id] = request.destination
            vehicle = by_vehicle[vehicle_id]
            states[vehicle_id] = VehicleState.LIVRE if at < vehicle.available_until else VehicleState.INDISPONIVEL
            result.events.append(Event(at, kind, vehicle_id, request.request_id))
        elif kind == "request":
            request = item
            assert isinstance(request, Request)
            options: list[tuple[float, str, float]] = []
            for vehicle_id, vehicle in by_vehicle.items():
                position = positions[vehicle_id]
                if states[vehicle_id] != VehicleState.LIVRE or position is None or request.modality not in vehicle.modalities:
                    continue
                pickup_km = between_km(estimator, position, request.origin)
                wait = 60 * pickup_km / config.speed_kmh
                finish = at + timedelta(minutes=wait + request.trip_minutes)
                if wait > config.max_pickup_minutes or finish > vehicle.available_until:
                    continue
                if any(c.vehicle_id == vehicle_id and c.start < finish and c.end > at for c in commitments):
                    continue
                options.append((pickup_km, vehicle_id, wait))
            if not options:
                result.excluded["unserved_no_eligible_vehicle_or_wait"] = result.excluded.get("unserved_no_eligible_vehicle_or_wait", 0) + 1
                result.events.append(Event(at, "unserved", None, request.request_id))
                continue
            pickup_km, vehicle_id, wait = min(options)
            states[vehicle_id] = VehicleState.INDO_BUSCAR_PASSAGEIRO
            result.pickup_km += pickup_km
            result.served_ids.append(request.request_id)
            result.vehicles_used.add(vehicle_id)
            result.wait_minutes.append(wait)
            arrival = at + timedelta(minutes=wait)
            push(arrival, 2, "pickup_arrival", (request, vehicle_id))
            push(arrival + timedelta(minutes=request.trip_minutes), 0, "trip_end", (request, vehicle_id))
            result.events.append(Event(at, "assigned", vehicle_id, request.request_id))
    return result
