"""Corridas encerradas geram evidência de ocupação, nunca de tempo livre."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime

from tcc_frota.availability.diagnostics import missing_value, timestamp
from tcc_frota.availability.timeline import EvidenceInterval, OperationalState
from tcc_frota.models import aware


def ride_intervals(
    rows: Iterable[Mapping[str, object]],
    *,
    timezone: str,
    as_of: datetime,
) -> tuple[list[EvidenceInterval], dict[str, int]]:
    """Consolida versões encerradas por solicitação; conflitos não viram fatos."""
    aware(as_of)
    audit: Counter[str] = Counter()
    completed: dict[str, set[tuple[str, datetime, datetime, str | None]]] = defaultdict(set)
    for row in rows:
        audit["input_rows"] += 1
        if row.get("TX_STATUS") != "CorridaEncerrada":
            audit["non_completed_rows"] += 1
            continue
        request = "" if missing_value(row.get("CD_SOLICITACAO")) else str(row["CD_SOLICITACAO"]).strip()
        vehicle = "" if missing_value(row.get("CD_VEICULO")) else str(row["CD_VEICULO"]).strip()
        if not request or not vehicle:
            audit["missing_request_or_vehicle"] += 1
            continue
        try:
            start = timestamp(row.get("DT_INICIO_REALIZADA"), timezone)
            end = timestamp(row.get("DT_FIM_REALIZADA"), timezone)
        except (ValueError, OverflowError):
            audit["invalid_timestamp"] += 1
            continue
        if start is None or end is None:
            audit["missing_interval_boundary"] += 1
            continue
        if end <= start:
            audit["nonpositive_interval"] += 1
            continue
        if end > as_of:
            audit["end_after_as_of"] += 1
            continue
        driver = None if missing_value(row.get("CD_MOTORISTA")) else str(row["CD_MOTORISTA"]).strip()
        interval = (vehicle, start, end, driver)
        if interval in completed[request]:
            audit["identical_completed_versions"] += 1
        completed[request].add(interval)
    result: list[EvidenceInterval] = []
    for request, versions in completed.items():
        if len(versions) != 1:
            audit["ambiguous_completed_requests"] += 1
            continue
        vehicle, start, end, driver = next(iter(versions))
        result.append(EvidenceInterval(vehicle, start, end, OperationalState.EM_CORRIDA, "corridas_v1", request, driver))
    audit["accepted_completed_requests"] = len(result)
    return result, dict(audit)
