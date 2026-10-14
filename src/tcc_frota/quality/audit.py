"""Auditoria agregada sem registrar valores pessoais."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class AuditSummary:
    rows: int
    missing_required: dict[str, int]
    duplicate_keys: int
    excluded: dict[str, int]

    def as_dict(self) -> dict[str, object]:
        return {
            "rows": self.rows,
            "missing_required": self.missing_required,
            "duplicate_keys": self.duplicate_keys,
            "excluded": self.excluded,
        }


def audit_rows(rows: Iterable[Mapping[str, object]], required: tuple[str, ...], key: str | None = None) -> AuditSummary:
    missing = Counter({name: 0 for name in required})
    seen: set[str] = set()
    duplicates = 0
    count = 0
    excluded = Counter()
    for row in rows:
        count += 1
        bad = [name for name in required if row.get(name) is None or str(row.get(name)).strip() == ""]
        for name in bad:
            missing[name] += 1
        if bad:
            excluded["missing_required"] += 1
        if key:
            value = row.get(key)
            if value is not None and str(value).strip():
                marker = str(value)
                if marker in seen:
                    duplicates += 1
                seen.add(marker)
    return AuditSummary(count, dict(missing), duplicates, dict(excluded))
