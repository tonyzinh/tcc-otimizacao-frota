"""Logs de status: mapeamento explícito, sem inferir disponibilidade a partir de Online."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Iterable, Mapping

from tcc_frota.availability.diagnostics import missing_value, timestamp
from tcc_frota.availability.timeline import EvidenceInterval, OperationalState
from tcc_frota.models import aware


_STATUS = {
    "Online": OperationalState.ONLINE_SEM_OCUPACAO_IDENTIFICADA,
    "Indisponivel": OperationalState.INDISPONIVEL,
    "Offline": OperationalState.DESCONHECIDO,
}


def status_intervals(
    rows: Iterable[Mapping[str, object]],
    *,
    timezone: str,
    as_of: datetime,
) -> tuple[list[EvidenceInterval], dict[str, int]]:
    """Aceita apenas logs com relação e intervalo completos no próprio extrato."""
    aware(as_of)
    audit: Counter[str] = Counter()
    groups: dict[str, set[tuple[str, datetime, datetime, OperationalState, str | None]]] = defaultdict(set)
    for row in rows:
        audit["input_rows"] += 1
        if row.get("qualidade_relacionamento") != "RELACIONADO" or row.get("qualidade_intervalo") != "COMPLETO":
            audit["unverified_relationship_or_interval"] += 1
            continue
        key = "" if missing_value(row.get("CD_LOG_STATUS_MOTORISTA")) else str(row["CD_LOG_STATUS_MOTORISTA"]).strip()
        vehicle = "" if missing_value(row.get("CD_VEICULO")) else str(row["CD_VEICULO"]).strip()
        state = _STATUS.get(str(row.get("TX_STATUS") or ""))
        if not key or not vehicle or state is None:
            audit["missing_key_vehicle_or_unknown_status"] += 1
            continue
        try:
            start = timestamp(row.get("inicio_evento"), timezone)
            end = timestamp(row.get("fim_evento"), timezone)
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
        value = (vehicle, start, end, state, driver)
        if value in groups[key]:
            audit["identical_versions"] += 1
        groups[key].add(value)
    result: list[EvidenceInterval] = []
    for key, versions in groups.items():
        if len(versions) != 1:
            audit["ambiguous_status_events"] += 1
            continue
        vehicle, start, end, state, driver = next(iter(versions))
        result.append(EvidenceInterval(vehicle, start, end, state, "eventos_status_motoristas", key, driver))
    audit["accepted_status_events"] = len(result)
    return result, dict(audit)
