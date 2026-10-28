"""RN016: nunca assumir equivalência direta de IDs entre sistemas."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class DriverLinkAudit:
    validated: bool
    matched: int
    unmatched_journey: int
    unmatched_status: int


def validate_driver_links(
    journey_ids: set[str],
    status_ids: set[str],
    verified_mapping: Mapping[str, str] | None = None,
) -> DriverLinkAudit:
    if verified_mapping is None:
        return DriverLinkAudit(False, 0, len(journey_ids), len(status_ids))
    if len(set(verified_mapping.values())) != len(verified_mapping):
        raise ValueError("mapeamento motorista não é um-para-um")
    if any(j not in journey_ids or s not in status_ids for j, s in verified_mapping.items()):
        raise ValueError("mapeamento contém ID sem evidência nas fontes")
    return DriverLinkAudit(
        True, len(verified_mapping), len(journey_ids - verified_mapping.keys()), len(status_ids - set(verified_mapping.values()))
    )
