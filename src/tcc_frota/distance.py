"""Unidades e proveniência de distâncias RN006–RN008, RN012."""
from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, isfinite, radians, sin, sqrt
from typing import Callable, Protocol

from .models import Position


@dataclass(frozen=True)
class DistanceMeasurement:
    km: float | None
    method: str
    source: str
    observed: bool


class PositionDistance(Protocol):
    name: str

    def measure(self, a: Position, b: Position) -> DistanceMeasurement: ...


class HaversineDistance:
    name = "haversine_estimated"

    def measure(self, a: Position, b: Position) -> DistanceMeasurement:
        return geodesic_estimate(a, b)


class RouteDistance:
    """Adaptador para roteador offline/futuro; sempre estimativa, nunca odômetro."""

    def __init__(self, route_km: Callable[[Position, Position], float], source: str):
        if not source:
            raise ValueError("fonte do roteador obrigatória")
        self.route_km = route_km
        self.source = source
        self.name = f"route_estimated:{source}"

    def measure(self, a: Position, b: Position) -> DistanceMeasurement:
        value = float(self.route_km(a, b))
        if value < 0 or not isfinite(value):
            raise ValueError("distância de rota inválida")
        return DistanceMeasurement(value, "route_estimated", self.source, False)


def between_km(estimator: PositionDistance, a: Position, b: Position) -> float:
    measurement = estimator.measure(a, b)
    if measurement.km is None or measurement.observed or measurement.km < 0 or not isfinite(measurement.km):
        raise ValueError("estimador posicional inválido")
    return measurement.km


def haversine_km(a: Position, b: Position) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (a.lat, a.lon, b.lat, b.lon))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371.0088 * 2 * asin(min(1.0, sqrt(h)))


def geodesic_estimate(a: Position, b: Position) -> DistanceMeasurement:
    return DistanceMeasurement(haversine_km(a, b), "haversine_straight_line", "coordinates", False)


def observed_meters(meters: float | str | None, field: str) -> DistanceMeasurement:
    if field not in {"NU_DISTPERCORRIDA", "NU_DISTANCIA_ACEITE_CHEGUEI"}:
        raise ValueError(f"campo sem semântica observada validada: {field}")
    if meters is None or meters == "":
        return DistanceMeasurement(None, "recorded_meters", field, True)
    value = float(meters)
    if value < 0:
        raise ValueError("distância negativa")
    return DistanceMeasurement(value / 1000.0, "recorded_meters", field, True)


def estimated_meters(meters: float | str | None, field: str) -> DistanceMeasurement:
    if field not in {"NU_DP", "NU_DR_REAL"}:
        raise ValueError("campo não classificado como estimativa")
    if meters is None or meters == "":
        return DistanceMeasurement(None, "source_estimate_meters", field, False)
    value = float(meters)
    if value < 0:
        raise ValueError("distância negativa")
    return DistanceMeasurement(value / 1000.0, "source_estimate_meters", field, False)
