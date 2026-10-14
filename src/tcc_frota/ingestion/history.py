"""Reconstrução conservadora de APP_SOLICITACAO_HIST."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping

from tcc_frota.models import aware


def parse_time(value: object) -> datetime | None:
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, datetime):
        return aware(value)
    return aware(datetime.fromisoformat(str(value).replace("Z", "+00:00")))


def parse_coordinate(value: object, *, latitude: bool) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip().replace(",", ".")
    parsed = float(text)
    if not (-90 <= parsed <= 90 if latitude else -180 <= parsed <= 180):
        raise ValueError("coordenada fora do intervalo")
    return parsed


@dataclass(frozen=True)
class Reconstructed:
    request_id: str
    created_at: datetime | None
    final_status: str
    final_at: datetime
    vehicle_id: str | None
    origin_lat: float | None
    origin_lon: float | None
    pickup_km_observed: float | None
    trip_km_observed: float | None


@dataclass(frozen=True)
class ReconstructionAudit:
    total_rows: int
    requests: int
    excluded: dict[str, int]
    dedup_disagreements: int
    timestamp_ties: int


def _recorded_km(row: Mapping[str, object], field: str) -> float | None:
    value = row.get(field)
    if value is None or str(value).strip() == "":
        return None
    number = float(value)
    if number < 0:
        raise ValueError("distância negativa")
    return number / 1000


def reconstruct_history(
    rows: Iterable[Mapping[str, object]],
    *,
    creation_field: str | None = None,
    creation_status: str | None = None,
) -> tuple[list[Reconstructed], ReconstructionAudit]:
    """Compara dois dedups; só aceita criação por campo explicitamente verificado.

    `creation_field` ou `creation_status` exigem semântica previamente verificada.
    Nenhum status é presumido como criação por padrão.
    """
    if creation_field == "DT_REGISTRO":
        raise ValueError("DT_REGISTRO da linha final não comprova criação")
    if creation_field and creation_status:
        raise ValueError("escolha uma única fonte de criação verificada")
    groups: dict[str, list[tuple[int, Mapping[str, object], datetime]]] = defaultdict(list)
    excluded: dict[str, int] = defaultdict(int)
    total = 0
    for index, row in enumerate(rows):
        total += 1
        request_id = str(row.get("CD_SOLICITACAO") or "").strip()
        if not request_id:
            excluded["missing_request_id"] += 1
            continue
        try:
            stamp = parse_time(row.get("DT_REGISTRO"))
        except ValueError:
            excluded["invalid_status_timestamp"] += 1
            continue
        if stamp is None:
            excluded["missing_status_timestamp"] += 1
            continue
        groups[request_id].append((index, row, stamp))
    results: list[Reconstructed] = []
    disagreements = ties = 0
    for request_id, group in sorted(groups.items()):
        latest = max(group, key=lambda item: (item[2], item[0]))
        if sum(item[2] == latest[2] for item in group) > 1:
            ties += 1
        def realized_key(item: tuple[int, Mapping[str, object], datetime]) -> tuple[datetime, datetime, int]:
            try:
                realized = parse_time(item[1].get("DT_INICIO_REALIZADA"))
            except ValueError:
                realized = None
            return (realized or datetime.min.replace(tzinfo=item[2].tzinfo), item[2], item[0])
        alternate = max(group, key=realized_key)
        if latest[0] != alternate[0]:
            disagreements += 1
        row = latest[1]
        created = None
        if creation_field:
            try:
                candidate_times = [parse_time(item[1].get(creation_field)) for item in group]
                created = min((stamp for stamp in candidate_times if stamp is not None), default=None)
            except ValueError:
                excluded["invalid_creation_timestamp"] += 1
        elif creation_status:
            matches = [item[2] for item in group if item[1].get("TX_STATUS") == creation_status]
            created = min(matches, default=None)
        if created is None:
            excluded["unverified_creation_timestamp"] += 1
        try:
            lat = parse_coordinate(row.get("TX_ORIGEM_LAT"), latitude=True)
            lon = parse_coordinate(row.get("TX_ORIGEM_LNG"), latitude=False)
            pickup = _recorded_km(row, "NU_DISTANCIA_ACEITE_CHEGUEI")
            trip = _recorded_km(row, "NU_DISTPERCORRIDA")
        except ValueError:
            excluded["invalid_spatial_or_distance"] += 1
            lat = lon = pickup = trip = None
        results.append(Reconstructed(request_id, created, str(row.get("TX_STATUS") or ""), latest[2], str(row.get("CD_VEICULO")) if row.get("CD_VEICULO") else None, lat, lon, pickup, trip))
    audit = ReconstructionAudit(total, len(results), dict(excluded), disagreements, ties)
    return results, audit
