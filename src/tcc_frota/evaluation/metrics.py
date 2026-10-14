"""Avaliação de cenários com origem e unidade explícitas."""
from __future__ import annotations

from tcc_frota.models import ScenarioResult


def summarize(result: ScenarioResult) -> dict[str, object]:
    return {
        "scenario": result.name,
        "dataset_kind": "synthetic",
        "baseline_type": result.baseline_type,
        "distance_method": result.distance_method,
        "observed_km": None,
        "distance_unit": "km",
        "distance_source": "synthetic_positions",
        "distance_components": {
            "pickup": "estimated_from_positions",
            "reposition": "estimated_from_positions",
            "return": "not_measured",
        },
        "estimated_pickup_km": round(result.pickup_km, 6),
        "estimated_reposition_km": round(result.reposition_km, 6),
        "return_km": result.return_km,
        "estimated_km_dead_total": round(result.km_dead_estimated, 6),
        "requests": len(result.request_ids),
        "served": len(result.served_ids),
        "coverage": result.coverage,
        "estimated_km_dead_per_served": result.km_dead_estimated / len(result.served_ids) if result.served_ids else None,
        "mean_estimated_wait_minutes": sum(result.wait_minutes) / len(result.wait_minutes) if result.wait_minutes else None,
        "vehicles_used": len(result.vehicles_used),
        "excluded": dict(result.excluded),
    }


def compare(baseline: ScenarioResult, proposed: ScenarioResult, *, minimum_coverage: float | None = None) -> dict[str, object]:
    if baseline.input_signature != proposed.input_signature or not baseline.input_signature:
        raise ValueError("condições iniciais ou restrições diferentes")
    if baseline.request_ids != proposed.request_ids or baseline.vehicle_ids != proposed.vehicle_ids:
        raise ValueError("universos incomparáveis")
    if baseline.distance_method != proposed.distance_method:
        raise ValueError("estimadores de distância diferentes")
    if minimum_coverage is not None and not 0 <= minimum_coverage <= 1:
        raise ValueError("cobertura mínima inválida")
    b, p = summarize(baseline), summarize(proposed)
    coverage_ok = (
        p["coverage"] is not None
        and b["coverage"] is not None
        and p["coverage"] >= b["coverage"] - 1e-12
        and (minimum_coverage is None or p["coverage"] >= minimum_coverage)
    )
    reduction = None
    if baseline.km_dead_estimated > 0 and coverage_ok:
        reduction = 100 * (baseline.km_dead_estimated - proposed.km_dead_estimated) / baseline.km_dead_estimated
    return {
        "baseline": b,
        "proposed": p,
        "estimated_km_reduction_percent": round(reduction, 6) if reduction is not None else None,
        "coverage_constraint_met": coverage_ok,
        "comparable_inputs": True,
        "interpretation": "contrafactual sintético; distância geodésica estimada; sem economia real observada",
    }
