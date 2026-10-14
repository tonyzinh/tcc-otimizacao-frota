"""Diagnóstico agregado de fontes operacionais sem imprimir valores pessoais."""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from tcc_frota.availability.contracts import SourceContract, locate_source
from tcc_frota.availability.io import iter_rows, source_schema


_MISSING = {"", "null", "none", "nan", "nat", "<na>"}


def missing_value(value: object) -> bool:
    return value is None or str(value).strip().casefold() in _MISSING


def timestamp(value: object, timezone: str) -> datetime | None:
    if missing_value(value):
        return None
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone))
    return parsed.astimezone(ZoneInfo(timezone))


def diagnose_source(
    root: Path,
    contract: SourceContract,
    *,
    timezone: str,
    period_start: date | None = None,
    period_end: date | None = None,
    max_distinct_keys: int = 1_000_000,
) -> dict[str, object]:
    paths = locate_source(root, contract.name)
    if not paths:
        return {"dataset": contract.name, "status": "AUSENTE", "files": 0}
    schemas = [source_schema(path) for path in paths]
    columns = set.intersection(*(set(schema) for schema in schemas))
    missing = sorted(set(contract.required) - columns)
    if missing:
        return {"dataset": contract.name, "status": "SCHEMA_INCOMPLETO", "files": len(paths), "missing_required": missing, "columns": sorted(columns)}
    selected = tuple(sorted(set(contract.required) | (set(contract.time_columns) & columns) | ({contract.key} if contract.key else set())))
    non_null: Counter[str] = Counter()
    invalid_time: Counter[str] = Counter()
    minimum: dict[str, datetime] = {}
    maximum: dict[str, datetime] = {}
    seen: set[str] = set()
    duplicate_keys = missing_keys = rows = outside_period = 0
    key_audit_truncated = False
    primary_time = next((name for name in contract.time_columns if name in selected), None)
    for path in paths:
        for row in iter_rows(path, selected):
            rows += 1
            for name, value in row.items():
                if not missing_value(value):
                    non_null[name] += 1
            if contract.key:
                key = "" if missing_value(row[contract.key]) else str(row[contract.key]).strip()
                if not key:
                    missing_keys += 1
                elif not key_audit_truncated:
                    if key in seen:
                        duplicate_keys += 1
                    elif len(seen) < max_distinct_keys:
                        seen.add(key)
                    else:
                        key_audit_truncated = True
                        seen.clear()
            for name in contract.time_columns:
                if name not in row or missing_value(row[name]):
                    continue
                try:
                    parsed = timestamp(row[name], timezone)
                except (ValueError, OverflowError):
                    invalid_time[name] += 1
                    continue
                if parsed is None:
                    continue
                minimum[name] = min(minimum.get(name, parsed), parsed)
                maximum[name] = max(maximum.get(name, parsed), parsed)
                if name == primary_time and ((period_start and parsed.date() < period_start) or (period_end and parsed.date() > period_end)):
                    outside_period += 1
    return {
        "dataset": contract.name,
        "status": "AUDITADO",
        "files": len(paths),
        "formats": sorted({path.suffix.lower().lstrip(".") for path in paths}),
        "rows": rows,
        "columns": sorted(columns),
        "non_null_by_required_or_time_field": dict(sorted(non_null.items())),
        "invalid_timestamp_by_field": dict(sorted(invalid_time.items())),
        "temporal_min": {name: value.isoformat() for name, value in sorted(minimum.items())},
        "temporal_max": {name: value.isoformat() for name, value in sorted(maximum.items())},
        "duplicate_key_rows": duplicate_keys if not key_audit_truncated else None,
        "missing_key_rows": missing_keys,
        "key_audit_truncated": key_audit_truncated,
        "outside_requested_period_by_primary_time": outside_period,
        "primary_time_field": primary_time,
        "timezone_interpretation": timezone,
        "timezone_confirmed_by_source": False,
    }
