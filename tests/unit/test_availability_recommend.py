from datetime import datetime
from zoneinfo import ZoneInfo

from tcc_frota.availability.forecast import CandidateForecast
from tcc_frota.availability.recommend import ServiceNeed, rank_experimental_candidates, rank_vehicles


def test_candidate_online_without_confirmed_availability_or_region_is_not_recommended():
    at = datetime(2026, 10, 14, 9, tzinfo=ZoneInfo("America/Sao_Paulo"))
    weak = CandidateForecast("v1", at, 0.9, None, 10, 1, "Online candidato")
    need = ServiceNeed(at, "regiao-1")
    assert rank_vehicles(need, [weak], eligible_vehicles={"v1"}) == []


def test_ranking_requires_same_region_time_eligibility_and_is_deterministic():
    at = datetime(2026, 10, 14, 9, tzinfo=ZoneInfo("America/Sao_Paulo"))
    values = [
        CandidateForecast("v2", at, 0.8, 0.7, 5, 1, "confirmed", "r1", True, True),
        CandidateForecast("v1", at, 0.8, 0.7, 5, 1, "confirmed", "r1", True, True),
        CandidateForecast("v3", at, 0.8, 0.9, 5, 1, "confirmed", "r2", True, True),
    ]
    ranked = rank_vehicles(ServiceNeed(at, "r1"), values, eligible_vehicles={"v1", "v2", "v3"})
    assert [item.vehicle_id for item in ranked] == ["v1", "v2"]


def test_experimental_ranking_labels_proxy_and_uses_location_freshness():
    at = datetime(2026, 10, 14, 9, tzinfo=ZoneInfo("America/Sao_Paulo"))
    predictions = [
        CandidateForecast("v2", at, 0.8, None, 5, 1, "proxy", "grid_1", location_age_minutes=60),
        CandidateForecast("v1", at, 0.8, None, 5, 1, "proxy", "grid_1", location_age_minutes=30),
        CandidateForecast("v3", at, 0.9, None, 5, 1, "proxy", "grid_1", location_age_minutes=300),
    ]
    ranked = rank_experimental_candidates(ServiceNeed(at, "grid_1"), predictions)
    assert [item.vehicle_id for item in ranked] == ["v1", "v2"]
    assert "não confirmada" in ranked[0].reason
