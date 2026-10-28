"""Linha do tempo conservadora com intervalos semiabertos [início, fim)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from tcc_frota.models import aware


class OperationalState(str, Enum):
    EM_CORRIDA = "EM_CORRIDA"
    EM_REPOSICIONAMENTO = "EM_REPOSICIONAMENTO"
    INDISPONIVEL = "INDISPONIVEL"
    FORA_DA_JORNADA = "FORA_DA_JORNADA"
    ONLINE_SEM_OCUPACAO_IDENTIFICADA = "ONLINE_SEM_OCUPACAO_IDENTIFICADA"
    DISPONIVEL_CONFIRMADO = "DISPONIVEL_CONFIRMADO"
    DESCONHECIDO = "DESCONHECIDO"


_PRIORITY = {
    OperationalState.EM_CORRIDA: 0,
    OperationalState.EM_REPOSICIONAMENTO: 1,
    OperationalState.INDISPONIVEL: 2,
    OperationalState.FORA_DA_JORNADA: 3,
    OperationalState.ONLINE_SEM_OCUPACAO_IDENTIFICADA: 4,
    OperationalState.DISPONIVEL_CONFIRMADO: 5,
    OperationalState.DESCONHECIDO: 6,
}


@dataclass(frozen=True)
class EvidenceInterval:
    vehicle_id: str
    start: datetime
    end: datetime
    state: OperationalState
    source: str
    reference: str | None = None
    driver_id: str | None = None
    plate: str | None = None

    def __post_init__(self) -> None:
        aware(self.start)
        aware(self.end)
        if not self.vehicle_id or self.end <= self.start:
            raise ValueError("evidência exige veículo e intervalo finito válido")


@dataclass(frozen=True)
class TimelineSegment:
    vehicle_id: str
    start: datetime
    end: datetime
    state: OperationalState
    confidence: str
    sources: tuple[str, ...]
    conflict: bool
    driver_id: str | None


def reconstruct_timeline(
    evidence: Iterable[EvidenceInterval],
    vehicles: Iterable[str],
    start: datetime,
    end: datetime,
) -> list[TimelineSegment]:
    """Reconstrói estados observáveis; lacunas continuam DESCONHECIDO."""
    aware(start)
    aware(end)
    if end <= start:
        raise ValueError("horizonte inválido")
    by_vehicle: dict[str, list[EvidenceInterval]] = defaultdict(list)
    for item in evidence:
        if item.start < end and item.end > start:
            by_vehicle[item.vehicle_id].append(item)
    result: list[TimelineSegment] = []
    for vehicle_id in sorted(set(vehicles) | set(by_vehicle)):
        if not vehicle_id:
            continue
        events: list[tuple[datetime, int, int]] = []
        items = by_vehicle[vehicle_id]
        for index, item in enumerate(items):
            events.append((max(start, item.start), 1, index))
            events.append((min(end, item.end), 0, index))
        events.sort()
        boundaries = sorted({start, end, *(at for at, _, _ in events)})
        active_items: dict[int, EvidenceInterval] = {}
        cursor = 0
        for left, right in zip(boundaries, boundaries[1:]):
            while cursor < len(events) and events[cursor][0] == left:
                _, kind, index = events[cursor]
                if kind == 0:
                    active_items.pop(index, None)
                else:
                    active_items[index] = items[index]
                cursor += 1
            if right <= left:
                continue
            active = list(active_items.values())
            state = min((item.state for item in active), key=_PRIORITY.get, default=OperationalState.DESCONHECIDO)
            drivers = {item.driver_id for item in active if item.driver_id}
            active_states = {item.state for item in active}
            conflicting_positive = state != OperationalState.DISPONIVEL_CONFIRMADO and any(
                item.state == OperationalState.DISPONIVEL_CONFIRMADO for item in active
            )
            overlapping_rides = len({item.reference for item in active if item.state == OperationalState.EM_CORRIDA and item.reference}) > 1
            contradictory_statuses = {
                OperationalState.ONLINE_SEM_OCUPACAO_IDENTIFICADA,
                OperationalState.INDISPONIVEL,
            } <= active_states
            contradictory_occupations = OperationalState.EM_CORRIDA in active_states and (
                OperationalState.INDISPONIVEL in active_states or OperationalState.EM_REPOSICIONAMENTO in active_states
            )
            conflict = conflicting_positive or len(drivers) > 1 or overlapping_rides or contradictory_statuses or contradictory_occupations
            if (len(drivers) > 1 or contradictory_statuses) and state not in {
                OperationalState.EM_CORRIDA,
                OperationalState.EM_REPOSICIONAMENTO,
            }:
                state = OperationalState.DESCONHECIDO
            if state == OperationalState.DESCONHECIDO:
                confidence = "SEM_EVIDENCIA"
            elif conflict:
                confidence = "CONFLITANTE"
            elif state == OperationalState.ONLINE_SEM_OCUPACAO_IDENTIFICADA:
                confidence = "CANDIDATO"
            elif state == OperationalState.EM_REPOSICIONAMENTO:
                confidence = "INFERIDO"
            else:
                confidence = "OBSERVADO"
            result.append(
                TimelineSegment(
                    vehicle_id,
                    left,
                    right,
                    state,
                    confidence,
                    tuple(sorted({item.source for item in active})),
                    conflict,
                    next(iter(drivers)) if len(drivers) == 1 else None,
                )
            )
    return result


def summarize_timeline(segments: Iterable[TimelineSegment]) -> dict[str, object]:
    seconds: defaultdict[str, float] = defaultdict(float)
    counts: defaultdict[str, int] = defaultdict(int)
    conflicts = 0
    vehicles: set[str] = set()
    for segment in segments:
        vehicles.add(segment.vehicle_id)
        seconds[segment.state.value] += (segment.end - segment.start).total_seconds()
        counts[segment.state.value] += 1
        conflicts += segment.conflict
    return {
        "vehicles": len(vehicles),
        "segments_by_state": dict(sorted(counts.items())),
        "hours_by_state": {state: round(value / 3600, 3) for state, value in sorted(seconds.items())},
        "conflicting_segments": conflicts,
    }
