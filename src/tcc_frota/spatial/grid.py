"""Grade determinística ajustada apenas com dados anteriores ao corte."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import floor

from tcc_frota.models import Position, Request, aware


@dataclass(frozen=True)
class Grid:
    cell_degrees: float
    zones: dict[str, Position]
    training_points: int

    def zone_for(self, lat: float, lon: float) -> str:
        row = floor(lat / self.cell_degrees)
        col = floor(lon / self.cell_degrees)
        return f"g{row}_{col}"


def fit_grid(requests: list[Request], cutoff: datetime, cell_degrees: float = 0.025, min_samples: int = 2) -> Grid:
    aware(cutoff)
    if cell_degrees <= 0 or min_samples < 1:
        raise ValueError("grade inválida")
    trained = [r for r in requests if r.created_at < cutoff]
    bins: dict[str, list[Position]] = {}
    for request in trained:
        pos = request.origin
        row = floor(pos.lat / cell_degrees)
        col = floor(pos.lon / cell_degrees)
        key = f"g{row}_{col}"
        bins.setdefault(key, []).append(pos)
    zones = {
        key: Position(key, sum(p.lat for p in points) / len(points), sum(p.lon for p in points) / len(points))
        for key, points in bins.items() if len(points) >= min_samples
    }
    return Grid(cell_degrees, zones, len(trained))
