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


@dataclass(frozen=True)
class ExperimentalCandidate:
    vehicle_id: str
    at: datetime
    region_proxy: str
    candidate_probability: float
    location_age_minutes: float
    reason: str


def rank_experimental_candidates(
    need: ServiceNeed,
    forecasts: Iterable[CandidateForecast],
    *,
    min_candidate_probability: float = 0.5,
    max_position_age_minutes: float = 120,
) -> list[ExperimentalCandidate]:
    """Ordena proxies para análise; não autoriza despacho nem afirma disponibilidade."""
    if not 0 <= min_candidate_probability <= 1 or max_position_age_minutes <= 0:
        raise ValueError("parâmetros experimentais inválidos")
    result: list[ExperimentalCandidate] = []
    for item in forecasts:
        if (
            item.target != need.at or item.region != need.origin_region
            or item.candidate_probability is None or item.candidate_probability < min_candidate_probability
            or item.location_age_minutes is None or item.location_age_minutes > max_position_age_minutes
        ):
            continue
        result.append(ExperimentalCandidate(
            item.vehicle_id, item.target, item.region, item.candidate_probability,
            item.location_age_minutes,
            "Online histórico sem ocupação conhecida + região Cobli inferida; disponibilidade futura não confirmada",
        ))
    return sorted(result, key=lambda item: (-item.candidate_probability, item.location_age_minutes, item.vehicle_id))


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
