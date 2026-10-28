from datetime import datetime
from zoneinfo import ZoneInfo

from tcc_frota.availability.statuses import status_intervals
from tcc_frota.availability.timeline import OperationalState, reconstruct_timeline

TZ = ZoneInfo("America/Sao_Paulo")


def at(hour: int) -> datetime:
    return datetime(2026, 10, 13, hour, tzinfo=TZ)


def row(key: str, status: str, *, finish: str = "2026-10-13 09:00:00") -> dict[str, str]:
    return {
        "CD_LOG_STATUS_MOTORISTA": key,
        "CD_MOTORISTA": "m1",
        "CD_VEICULO": "v1",
        "TX_STATUS": status,
        "inicio_evento": "2026-10-13 08:00:00",
        "fim_evento": finish,
        "qualidade_intervalo": "COMPLETO",
        "qualidade_relacionamento": "RELACIONADO",
    }


def test_online_is_candidate_offline_is_unknown_and_open_event_excluded():
    online = row("l1", "Online")
    offline = row("l2", "Offline")
    offline["inicio_evento"] = "2026-10-13 09:00:00"
    offline["fim_evento"] = "2026-10-13 10:00:00"
    open_event = row("l3", "Indisponivel", finish="NaT")
    open_event["qualidade_intervalo"] = "SEM_FIM"
    evidence, audit = status_intervals([online, offline, open_event], timezone="America/Sao_Paulo", as_of=at(11))
    timeline = reconstruct_timeline(evidence, ["v1"], at(8), at(10))
    assert [segment.state for segment in timeline] == [
        OperationalState.ONLINE_SEM_OCUPACAO_IDENTIFICADA,
        OperationalState.DESCONHECIDO,
    ]
    assert audit["unverified_relationship_or_interval"] == 1


def test_status_key_conflict_and_two_drivers_cannot_confirm_vehicle_state():
    changed = row("l1", "Indisponivel")
    second = row("l2", "Online")
    second["CD_MOTORISTA"] = "m2"
    evidence, audit = status_intervals([row("l1", "Online"), changed, second], timezone="America/Sao_Paulo", as_of=at(11))
    assert audit["ambiguous_status_events"] == 1
    assert len(evidence) == 1
    another = row("l3", "Indisponivel")
    status, _ = status_intervals([another, second], timezone="America/Sao_Paulo", as_of=at(11))
    timeline = reconstruct_timeline(status, ["v1"], at(8), at(9))
    assert timeline[0].state == OperationalState.DESCONHECIDO
    assert timeline[0].conflict


def test_same_driver_overlapping_online_and_indisponivel_is_unknown():
    online = row("l1", "Online")
    blocked = row("l2", "Indisponivel")
    evidence, _ = status_intervals([online, blocked], timezone="America/Sao_Paulo", as_of=at(11))
    timeline = reconstruct_timeline(evidence, ["v1"], at(8), at(9))
    assert timeline[0].state == OperationalState.DESCONHECIDO
    assert timeline[0].conflict
