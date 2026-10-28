"""Contratos pequenos, sem dependência de Databricks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps precisam de fuso explícito")
    return value


@dataclass(frozen=True)
class Position:
    zone: str
    lat: float
    lon: float

    def __post_init__(self) -> None:
        if not self.zone or not -90 <= self.lat <= 90 or not -180 <= self.lon <= 180:
            raise ValueError("posição inválida")


@dataclass(frozen=True)
class Request:
    request_id: str
    created_at: datetime
    origin: Position
    destination: Position
    trip_minutes: float
    modality: str = "PF"

    def __post_init__(self) -> None:
        aware(self.created_at)
        if not self.request_id or self.trip_minutes <= 0:
            raise ValueError("solicitação inválida")


@dataclass(frozen=True)
class Vehicle:
    vehicle_id: str
    position: Position | None
    available_from: datetime
    available_until: datetime
    active: bool = True
    driver_ready: bool = True
    modalities: tuple[str, ...] = ("PF",)

    def __post_init__(self) -> None:
        aware(self.available_from)
        aware(self.available_until)
        if not self.vehicle_id or self.available_until <= self.available_from:
            raise ValueError("janela de veículo inválida")


@dataclass(frozen=True)
class Commitment:
    """Ocupação externa que conta mesmo fora da modalidade do experimento."""

    vehicle_id: str
    start: datetime
    end: datetime
    modality: str
    end_position: Position | None = None

    def __post_init__(self) -> None:
        aware(self.start)
        aware(self.end)
        if self.end <= self.start:
            raise ValueError("intervalo de compromisso inválido")


@dataclass(frozen=True)
class Recommendation:
    vehicle_id: str
    origin: Position
    destination: Position
    start_at: datetime
    distance_km: float


class VehicleState(str, Enum):
    INDISPONIVEL = "INDISPONIVEL"
    LIVRE = "LIVRE"
    REPOSICIONANDO = "REPOSICIONANDO"
    INDO_BUSCAR_PASSAGEIRO = "INDO_BUSCAR_PASSAGEIRO"
    EM_VIAGEM = "EM_VIAGEM"


@dataclass(frozen=True)
class Event:
    at: datetime
    kind: str
    vehicle_id: str | None = None
    request_id: str | None = None


@dataclass
class ScenarioResult:
    name: str
    request_ids: tuple[str, ...]
    vehicle_ids: tuple[str, ...]
    served_ids: list[str] = field(default_factory=list)
    excluded: dict[str, int] = field(default_factory=dict)
    pickup_km: float = 0.0
    reposition_km: float = 0.0
    return_km: float | None = None
    events: list[Event] = field(default_factory=list)
    wait_minutes: list[float] = field(default_factory=list)
    vehicles_used: set[str] = field(default_factory=set)
    input_signature: str = ""
    distance_method: str = "haversine_estimated"
    baseline_type: str = "simplified_no_repositioning"

    @property
    def km_dead_estimated(self) -> float:
        return self.pickup_km + self.reposition_km + (self.return_km or 0.0)

    @property
    def coverage(self) -> float | None:
        return len(self.served_ids) / len(self.request_ids) if self.request_ids else None
