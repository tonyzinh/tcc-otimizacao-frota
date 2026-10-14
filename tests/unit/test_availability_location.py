from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tcc_frota.availability.location import grid_region, last_vehicle_positions
from tcc_frota.availability.timeline import EvidenceInterval, OperationalState


TZ = ZoneInfo("America/Sao_Paulo")
CUTOFF = datetime(2026, 10, 13, 20, tzinfo=TZ)


def cobli(at: str, *, kind: str = "stops", plate: str = "ABC1234", lat: str = "-20.30", lon: str = "-40.30"):
    return {"placa": plate, "TYPE": kind, "END_ADDRESS_DATETIME": at, "END_ADDRESS_LATITUDE": lat, "END_ADDRESS_LONGITUDE": lon}


def status(vehicle: str, plate: str = "ABC1234"):
    return EvidenceInterval(vehicle, CUTOFF - timedelta(hours=3), CUTOFF, OperationalState.ONLINE_SEM_OCUPACAO_IDENTIFICADA, "status", plate=plate)


def test_cobli_stop_is_only_fresh_position_not_availability():
    rows = [cobli("2026-10-13 19:30:00")]
    positions, audit = last_vehicle_positions(rows, [status("v1")], timezone="America/Sao_Paulo", cutoff=CUTOFF)
    assert positions["v1"].region == grid_region(-20.3, -40.3)
    assert positions["v1"].age_minutes_at_cutoff == 30
    assert audit["matched_vehicles"] == 1
    assert not hasattr(positions["v1"], "availability_probability")


def test_stale_future_invalid_and_ambiguous_plate_are_rejected():
    rows = [
        cobli("2026-10-13 16:00:00"),
        cobli("2026-10-13 20:10:00"),
        cobli("2026-10-13 19:30:00", lat="999"),
        cobli("2026-10-13 19:20:00"),
    ]
    positions, audit = last_vehicle_positions(rows, [status("v1"), status("v2")], timezone="America/Sao_Paulo", cutoff=CUTOFF)
    assert positions == {}
    assert audit["outside_freshness_window"] == 2
    assert audit["invalid_time_or_coordinate"] == 1
    assert audit["unmatched_or_ambiguous_plate_at_time"] == 1


def test_unique_plate_in_24h_can_give_explicitly_weaker_location_proxy():
    recent_status = EvidenceInterval(
        "v1", CUTOFF - timedelta(hours=3), CUTOFF - timedelta(hours=2),
        OperationalState.ONLINE_SEM_OCUPACAO_IDENTIFICADA, "status", plate="ABC1234",
    )
    positions, audit = last_vehicle_positions(
        [cobli("2026-10-13 19:30:00")], [recent_status],
        timezone="America/Sao_Paulo", cutoff=CUTOFF,
    )
    assert positions["v1"].method == "cobli_endpoint_unique_plate_24h_grid_0.05_degree"
    assert audit["matched_by_unique_plate_24h"] == 1
