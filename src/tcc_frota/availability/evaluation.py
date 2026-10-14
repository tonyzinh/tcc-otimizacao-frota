"""Backtest do proxy de candidatura; não mede disponibilidade confirmada."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Iterable

from tcc_frota.availability.forecast import CandidateForecast
from tcc_frota.availability.timeline import OperationalState, TimelineSegment


_NEGATIVE = {
    OperationalState.EM_CORRIDA,
    OperationalState.EM_REPOSICIONAMENTO,
    OperationalState.INDISPONIVEL,
    OperationalState.FORA_DA_JORNADA,
}


def evaluate_candidate_proxy(
    predictions: Iterable[CandidateForecast],
    observed_segments: Iterable[TimelineSegment],
) -> dict[str, object]:
    """Compara taxa prevista ao estado inferido no início da faixa futura."""
    by_vehicle: dict[str, list[TimelineSegment]] = defaultdict(list)
    for item in observed_segments:
        by_vehicle[item.vehicle_id].append(item)
    brier = 0.0
    matched = unknown = without_forecast = 0
    observed_positive = 0
    for prediction in predictions:
        if prediction.candidate_probability is None:
            without_forecast += 1
            continue
        applicable = next((item for item in by_vehicle[prediction.vehicle_id] if item.start <= prediction.target < item.end), None)
        if applicable is None or applicable.conflict or applicable.state == OperationalState.DESCONHECIDO:
            unknown += 1
            continue
        if applicable.state == OperationalState.ONLINE_SEM_OCUPACAO_IDENTIFICADA:
            label = 1
        elif applicable.state in _NEGATIVE:
            label = 0
        else:
            unknown += 1
            continue
        observed_positive += label
        brier += (prediction.candidate_probability - label) ** 2
        matched += 1
    return {
        "evaluated_slots": matched,
        "unknown_target_slots": unknown,
        "slots_without_forecast": without_forecast,
        "observed_candidate_slots": observed_positive,
        "brier_candidate_proxy": round(brier / matched, 6) if matched else None,
        "interpretation": "avalia estado Online sem ocupação conhecida; não valida disponibilidade física nem recomendação",
    }
