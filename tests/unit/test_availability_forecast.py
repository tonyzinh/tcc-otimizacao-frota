from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from tcc_frota.availability.forecast import HistoricalCandidateBaseline
from tcc_frota.availability.timeline import OperationalState, TimelineSegment

TZ = ZoneInfo("America/Sao_Paulo")


def segment(start, end, state):
    return TimelineSegment("v1", start, end, state, "OBSERVADO", ("test",), False, None)


def test_baseline_distinguishes_candidate_from_confirmed_availability():
    cutoff = datetime(2026, 10, 13, 20, tzinfo=TZ)
    target = datetime(2026, 10, 14, 9, tzinfo=TZ)
    history = []
    for days in (7, 14, 21, 28):
        start = target - timedelta(days=days)
        history.append(segment(start, start + timedelta(hours=1), OperationalState.ONLINE_SEM_OCUPACAO_IDENTIFICADA))
    history.append(segment(target - timedelta(days=35), target - timedelta(days=35) + timedelta(hours=1), OperationalState.EM_CORRIDA))
    model = HistoricalCandidateBaseline(cutoff, history)
    prediction = model.predict("v1", target)
    assert prediction.candidate_probability == pytest.approx(0.8)
    assert prediction.availability_probability is None
    assert prediction.region is None


def test_future_segments_and_unknown_do_not_create_training_labels():
    cutoff = datetime(2026, 10, 13, 20, tzinfo=TZ)
    target = datetime(2026, 10, 14, 9, tzinfo=TZ)
    with pytest.raises(ValueError):
        HistoricalCandidateBaseline(
            cutoff, [segment(target, target + timedelta(hours=1), OperationalState.ONLINE_SEM_OCUPACAO_IDENTIFICADA)]
        )
    unknown = segment(target - timedelta(days=7), target - timedelta(days=7) + timedelta(hours=1), OperationalState.DESCONHECIDO)
    assert HistoricalCandidateBaseline(cutoff, [unknown]).predict("v1", target).candidate_probability is None
