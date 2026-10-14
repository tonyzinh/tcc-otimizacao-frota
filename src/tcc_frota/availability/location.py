"""Última posição Cobli ligada por placa e tempo a um único veículo."""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Mapping

from tcc_frota.availability.diagnostics import missing_value, timestamp
from tcc_frota.availability.timeline import EvidenceInterval
from tcc_frota.models import aware


@dataclass(frozen=True)
class PositionEvidence:
    vehicle_id: str
    region: str
    observed_at: datetime
    age_minutes_at_cutoff: float
    method: str = "cobli_endpoint_active_status_grid_0.05_degree"


def grid_region(latitude: float, longitude: float, *, cell_degrees: float = 0.05) -> str:
    if not math.isfinite(latitude) or not math.isfinite(longitude) or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("coordenada inválida")
    if cell_degrees <= 0:
        raise ValueError("tamanho de célula inválido")
    return f"grid_{cell_degrees:g}_{math.floor(latitude / cell_degrees)}_{math.floor(longitude / cell_degrees)}"


def last_vehicle_positions(
    rows: Iterable[Mapping[str, object]],
    status_evidence: Iterable[EvidenceInterval],
    *,
    timezone: str,
    cutoff: datetime,
    max_age_minutes: float = 120,
) -> tuple[dict[str, PositionEvidence], dict[str, int]]:
    """Usa endpoints físicos; `stops` nunca vira prova de disponibilidade."""
    aware(cutoff)
    if max_age_minutes <= 0:
        raise ValueError("idade máxima inválida")
    audit: Counter[str] = Counter()
    latest: dict[str, tuple[datetime, float, float]] = {}
    oldest_allowed = cutoff - timedelta(minutes=max_age_minutes)
    for row in rows:
        audit["input_rows"] += 1
        plate = "" if missing_value(row.get("placa")) else str(row["placa"]).strip().upper()
        if not plate or row.get("TYPE") not in {"trips", "stops"}:
            audit["missing_plate_or_unknown_type"] += 1
            continue
        try:
            at = timestamp(row.get("END_ADDRESS_DATETIME"), timezone)
            if at is None or at > cutoff or at < oldest_allowed:
                audit["outside_freshness_window"] += 1
                continue
            lat = float(row["END_ADDRESS_LATITUDE"])
            lon = float(row["END_ADDRESS_LONGITUDE"])
            grid_region(lat, lon)
        except (ValueError, TypeError, OverflowError):
            audit["invalid_time_or_coordinate"] += 1
            continue
        if plate not in latest or at > latest[plate][0]:
            latest[plate] = (at, lat, lon)
    by_plate: dict[str, list[EvidenceInterval]] = defaultdict(list)
    for item in status_evidence:
        if item.plate:
            by_plate[item.plate.upper()].append(item)
    result: dict[str, PositionEvidence] = {}
    for plate, (at, lat, lon) in latest.items():
        matches = {item.vehicle_id for item in by_plate[plate] if item.start <= at < item.end}
        method = "cobli_endpoint_active_status_grid_0.05_degree"
        if len(matches) != 1:
            matches = {
                item.vehicle_id for item in by_plate[plate]
                if item.start < cutoff and item.end > cutoff - timedelta(hours=24)
            }
            method = "cobli_endpoint_unique_plate_24h_grid_0.05_degree"
        if len(matches) != 1:
            audit["unmatched_or_ambiguous_plate_at_time"] += 1
            continue
        vehicle = next(iter(matches))
        candidate = PositionEvidence(vehicle, grid_region(lat, lon), at, round((cutoff - at).total_seconds() / 60, 3), method)
        if vehicle not in result or at > result[vehicle].observed_at:
            result[vehicle] = candidate
        audit["matched_by_active_status" if method.startswith("cobli_endpoint_active") else "matched_by_unique_plate_24h"] += 1
    audit["matched_vehicles"] = len(result)
    return result, dict(audit)
