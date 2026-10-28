from datetime import UTC, datetime, timedelta

import pytest

from tcc_frota.ingestion.es_bridge import REQUIRED_EVIDENCE, plan_from_historical_forecast
from tcc_frota.models import Position, Vehicle
from tcc_frota.optimization.greedy import greedy_plan


def test_current_temporal_gold_cannot_reach_planner():
    with pytest.raises(ValueError, match="verified_request_origin_zones"):
        plan_from_historical_forecast(
            {"spatial_status": "origin_unavailable", "expected_by_hour": {"8": 4}}, [], {}, datetime(2026, 1, 2, tzinfo=UTC), evidence={}
        )


def test_verified_adapter_delegates_to_existing_greedy():
    start = datetime(2026, 1, 2, tzinfo=UTC)
    center = Position("center", -20.3, -40.3)
    east = Position("east", -20.3, -40.28)
    vehicle = Vehicle("synthetic-v", center, start, start + timedelta(hours=3))
    forecast = {"spatial_status": "verified_request_origin", "expected_by_zone": {"east": 2.0}}
    evidence = dict.fromkeys(REQUIRED_EVIDENCE, True)
    via_adapter = plan_from_historical_forecast(forecast, [vehicle], {"east": east}, start, evidence=evidence)
    direct = greedy_plan([vehicle], {"east": east}, {"east": 2.0}, start)
    assert via_adapter == direct
    evidence["occupation_complete"] = False
    with pytest.raises(ValueError, match="occupation_complete"):
        plan_from_historical_forecast(forecast, [vehicle], {"east": east}, start, evidence=evidence)
