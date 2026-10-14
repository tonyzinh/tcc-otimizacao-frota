"""Evidence gate between prepared historical demand and the existing planner."""
from __future__ import annotations

from datetime import datetime
from typing import Mapping

from tcc_frota.models import Commitment, Position, Vehicle
from tcc_frota.optimization.greedy import Plan, greedy_plan


REQUIRED_EVIDENCE = (
    "creation_time_verified", "request_origin_verified", "fleet_eligibility_verified",
    "vehicle_positions_verified", "occupation_complete", "journeys_verified",
)


def plan_from_historical_forecast(
    forecast: Mapping[str, object], vehicles: list[Vehicle], zones: dict[str, Position],
    start_at: datetime, *, evidence: Mapping[str, bool],
    commitments: tuple[Commitment, ...] = (), min_coverage: float = 0.0,
) -> Plan:
    """Call the original greedy planner only for independently validated inputs.

    This is an experiment adapter, not authorization for operational dispatch.
    The current Elasticsearch Gold has no request-origin zones and fails here.
    """
    missing = [name for name in REQUIRED_EVIDENCE if evidence.get(name) is not True]
    if forecast.get("spatial_status") != "verified_request_origin":
        missing.append("verified_request_origin_zones")
    demand = forecast.get("expected_by_zone")
    if not isinstance(demand, dict) or not demand:
        missing.append("expected_by_zone")
    if not vehicles or not zones:
        missing.append("fleet_or_zones")
    if missing:
        raise ValueError("plano histórico bloqueado: " + ", ".join(missing))
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in demand.values()):
        raise ValueError("previsão por zona inválida")
    return greedy_plan(vehicles, zones, demand, start_at, commitments=commitments,
                       min_coverage=min_coverage)
