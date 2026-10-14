"""Ranking conservador; não recomenda veículos sem probabilidade e região validadas."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from tcc_frota.availability.forecast import CandidateForecast
from tcc_frota.models import aware


@dataclass(frozen=True)
class ServiceNeed:
    at: datetime
    origin_region: str

    def __post_init__(self) -> None:
        aware(self.at)
        if not self.origin_region:
            raise ValueError("região de origem obrigatória")


@dataclass(frozen=True)
class RankedVehicle:
    vehicle_id: str
    score: float
    availability_probability: float
    reason: str


def rank_vehicles(
    need: ServiceNeed,
    forecasts: Iterable[CandidateForecast],
    *,
    eligible_vehicles: set[str],
    min_probability: float = 0.5,
) -> list[RankedVehicle]:
    if not 0 <= min_probability <= 1:
        raise ValueError("limiar inválido")
    ranked: list[RankedVehicle] = []
    for prediction in forecasts:
        if prediction.target != need.at or prediction.vehicle_id not in eligible_vehicles:
            continue
        probability = prediction.availability_probability
        if (
            probability is None or probability < min_probability
            or not prediction.availability_validated or not prediction.region_validated
            or prediction.region != need.origin_region
        ):
            continue
        if not 0 <= probability <= 1:
            raise ValueError("probabilidade inválida")
        ranked.append(RankedVehicle(
            prediction.vehicle_id,
            probability,
            probability,
            "elegibilidade e região confirmadas; probabilidade de disponibilidade informada",
        ))
    return sorted(ranked, key=lambda item: (-item.score, item.vehicle_id))
