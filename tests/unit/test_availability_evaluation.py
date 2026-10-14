from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tcc_frota.availability.evaluation import evaluate_candidate_proxy
from tcc_frota.availability.forecast import CandidateForecast
from tcc_frota.availability.timeline import OperationalState, TimelineSegment


def test_backtest_ignores_unknown_and_scores_only_observed_proxy():
    at = datetime(2026, 10, 14, 9, tzinfo=ZoneInfo("America/Sao_Paulo"))
    predictions = [
        CandidateForecast("v1", at, 0.8, None, 4, 1, "proxy"),
        CandidateForecast("v2", at, 0.2, None, 1, 4, "proxy"),
        CandidateForecast("v3", at, 0.9, None, 4, 1, "proxy"),
    ]
    observed = [
        TimelineSegment("v1", at, at + timedelta(hours=1), OperationalState.ONLINE_SEM_OCUPACAO_IDENTIFICADA, "CANDIDATO", ("status",), False, None),
        TimelineSegment("v2", at, at + timedelta(hours=1), OperationalState.EM_CORRIDA, "OBSERVADO", ("rides",), False, None),
        TimelineSegment("v3", at, at + timedelta(hours=1), OperationalState.DESCONHECIDO, "SEM_EVIDENCIA", (), False, None),
    ]
    report = evaluate_candidate_proxy(predictions, observed)
    assert report["evaluated_slots"] == 2
    assert report["unknown_target_slots"] == 1
    assert report["brier_candidate_proxy"] == 0.04
