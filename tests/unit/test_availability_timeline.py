from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tcc_frota.availability.rides import ride_intervals
from tcc_frota.availability.timeline import EvidenceInterval, OperationalState, reconstruct_timeline

TZ = ZoneInfo("America/Sao_Paulo")


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=TZ)


def test_midnight_ride_and_half_open_boundary_leave_unknown_gap():
    rows = [
        {
            "CD_SOLICITACAO": "r1",
            "CD_VEICULO": "v1",
            "CD_MOTORISTA": "m1",
            "TX_STATUS": "CorridaEncerrada",
            "DT_INICIO_REALIZADA": "2026-10-12 23:50:00",
            "DT_FIM_REALIZADA": "2026-10-13 00:20:00",
        }
    ]
    rides, audit = ride_intervals(rows, timezone="America/Sao_Paulo", as_of=at(13, 1))
    timeline = reconstruct_timeline(rides, ["v1"], at(12, 23), at(13, 1))
    assert audit["accepted_completed_requests"] == 1
    assert [(segment.state, segment.end) for segment in timeline] == [
        (OperationalState.DESCONHECIDO, at(12, 23, 50)),
        (OperationalState.EM_CORRIDA, at(13, 0, 20)),
        (OperationalState.DESCONHECIDO, at(13, 1)),
    ]


def test_overlapping_rides_keep_occupation_but_mark_conflict():
    rides = [
        EvidenceInterval("v", at(13, 8), at(13, 9), OperationalState.EM_CORRIDA, "corridas_v1", "r1", "m1"),
        EvidenceInterval("v", at(13, 8, 30), at(13, 9, 30), OperationalState.EM_CORRIDA, "corridas_v1", "r2", "m2"),
    ]
    timeline = reconstruct_timeline(rides, ["v"], at(13, 8), at(13, 10))
    assert timeline[1].state == OperationalState.EM_CORRIDA
    assert timeline[1].conflict and timeline[1].driver_id is None
    assert timeline[-1].state == OperationalState.DESCONHECIDO


def test_online_and_cobli_stop_never_override_active_ride():
    ride = EvidenceInterval("v", at(13, 8), at(13, 9), OperationalState.EM_CORRIDA, "corridas_v1", "r1")
    online = EvidenceInterval("v", at(13, 7), at(13, 10), OperationalState.ONLINE_SEM_OCUPACAO_IDENTIFICADA, "status")
    timeline = reconstruct_timeline([ride, online], ["v"], at(13, 8), at(13, 9))
    assert len(timeline) == 1 and timeline[0].state == OperationalState.EM_CORRIDA


def test_missing_end_cannot_become_infinite_interval():
    with pytest.raises(ValueError):
        EvidenceInterval("v", at(13, 8), at(13, 8), OperationalState.INDISPONIVEL, "status")


def test_conflicting_completed_versions_excluded_and_future_ride_excluded():
    base = {
        "CD_SOLICITACAO": "r1",
        "CD_VEICULO": "v",
        "TX_STATUS": "CorridaEncerrada",
        "DT_INICIO_REALIZADA": "2026-10-13 08:00:00",
        "DT_FIM_REALIZADA": "2026-10-13 09:00:00",
    }
    other = dict(base, DT_FIM_REALIZADA="2026-10-13 09:10:00")
    future = dict(base, CD_SOLICITACAO="r2", DT_FIM_REALIZADA="2026-10-13 12:00:00")
    intervals, audit = ride_intervals([base, dict(base), other, future], timezone="America/Sao_Paulo", as_of=at(13, 10))
    assert not intervals
    assert audit["identical_completed_versions"] == 1
    assert audit["ambiguous_completed_requests"] == 1
    assert audit["end_after_as_of"] == 1


def test_state_without_evidence_is_unknown_not_available():
    timeline = reconstruct_timeline([], ["v"], at(13, 8), at(13, 9))
    assert timeline[0].state == OperationalState.DESCONHECIDO
    assert timeline[0].confidence == "SEM_EVIDENCIA"
