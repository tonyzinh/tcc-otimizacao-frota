"""Baseline D+1 da condição de candidato, separado de disponibilidade real."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from tcc_frota.availability.timeline import OperationalState, TimelineSegment
from tcc_frota.models import aware


_NEGATIVE = {
    OperationalState.EM_CORRIDA,
    OperationalState.EM_REPOSICIONAMENTO,
    OperationalState.INDISPONIVEL,
    OperationalState.FORA_DA_JORNADA,
}


@dataclass(frozen=True)
class CandidateForecast:
    vehicle_id: str
    target: datetime
    candidate_probability: float | None
    availability_probability: float | None
    positive_observed_hours: float
    negative_observed_hours: float
    reason: str
    region: str | None = None
    availability_validated: bool = False
    region_validated: bool = False
    confidence_level: str = "NAO_CALIBRADA"


class HistoricalCandidateBaseline:
    """Conta horas históricas por veículo/dia-da-semana/hora antes do corte."""

    def __init__(self, cutoff: datetime, segments: Iterable[TimelineSegment]):
        aware(cutoff)
        self.cutoff = cutoff
        self.hours: dict[tuple[str, int, int], list[float]] = defaultdict(lambda: [0.0, 0.0])
        for segment in segments:
            if segment.end > cutoff:
                raise ValueError("segmento posterior ao corte D+1")
            if segment.state == OperationalState.ONLINE_SEM_OCUPACAO_IDENTIFICADA:
                side = 0
            elif segment.state in _NEGATIVE:
                side = 1
            else:
                continue
            cursor = segment.start
            while cursor < segment.end:
                boundary = cursor.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                next_at = min(segment.end, boundary)
                if next_at <= cursor:
                    raise ValueError("janela temporal inválida")
                self.hours[(segment.vehicle_id, cursor.weekday(), cursor.hour)][side] += (next_at - cursor).total_seconds() / 3600
                cursor = next_at

    def predict(self, vehicle_id: str, target: datetime, *, min_observed_hours: float = 3.0) -> CandidateForecast:
        aware(target)
        if target.tzinfo != self.cutoff.tzinfo or target.date() != self.cutoff.date() + timedelta(days=1):
            raise ValueError("alvo deve estar no dia local D+1 e no fuso do corte")
        positive, negative = self.hours.get((vehicle_id, target.weekday(), target.hour), [0.0, 0.0])
        observed = positive + negative
        candidate = positive / observed if observed >= min_observed_hours and positive > 0 else None
        reason = "taxa histórica de Online sem ocupação identificada; não é disponibilidade confirmada" if candidate is not None else "evidência positiva/negativa insuficiente na mesma faixa semanal"
        return CandidateForecast(
            vehicle_id, target, candidate, None, round(positive, 3), round(negative, 3), reason,
            confidence_level="PROXY_NAO_CALIBRADO" if candidate is not None else "SEM_EVIDENCIA_SUFICIENTE",
        )
