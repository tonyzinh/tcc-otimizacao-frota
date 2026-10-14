"""Execução reproduzível com artefatos agregados."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from tcc_frota.demand.forecast import forecast_error, forecast_hour
from tcc_frota.distance import HaversineDistance
from tcc_frota.evaluation.metrics import compare
from tcc_frota.optimization.greedy import greedy_plan
from tcc_frota.simulation.engine import SimulationConfig, simulate
from tcc_frota.synthetic.generator import SyntheticDataset, make_synthetic


def run_dataset(
    dataset: SyntheticDataset,
    minimum_coverage: float = 0.75,
    *,
    max_reposition_km: float = 12,
    adherence: float = 1.0,
) -> dict[str, object]:
    if not 0 <= adherence <= 1:
        raise ValueError("adesão hipotética inválida")
    seed = dataset.seed
    fleet_size = len(dataset.vehicles)
    estimator = HaversineDistance()
    cutoff = datetime.combine(dataset.target_date - timedelta(days=1), time(20), tzinfo=timezone.utc)
    plan_start = datetime.combine(dataset.target_date, time(7), tzinfo=timezone.utc)
    simulation_end = datetime.combine(dataset.target_date, time(10), tzinfo=timezone.utc)
    forecast = forecast_hour(dataset.historical + dataset.evaluation, dataset.zones, dataset.target_date, 8, cutoff)
    plan = greedy_plan(
        dataset.vehicles, dataset.zones, forecast.expected_by_zone, plan_start,
        capacity_per_vehicle=2, min_coverage=minimum_coverage,
        max_pickup_km=15, max_reposition_km=max_reposition_km,
        estimator=estimator,
    )
    config = SimulationConfig(plan_start, simulation_end)
    baseline = simulate("baseline_simplified", dataset.evaluation, dataset.vehicles, config, estimator=estimator)
    applied = plan.recommendations[:int(len(plan.recommendations) * adherence)]
    proposed = simulate("preventive_greedy", dataset.evaluation, dataset.vehicles, config, recommendations=applied, estimator=estimator)
    result = compare(baseline, proposed, minimum_coverage=minimum_coverage)
    run_id = hashlib.sha256(f"{baseline.input_signature}:{seed}:{minimum_coverage}:{max_reposition_km}:{adherence}".encode()).hexdigest()[:12]
    movements: dict[tuple[str, str], tuple[int, float]] = defaultdict(lambda: (0, 0.0))
    for rec in plan.recommendations:
        key = (rec.origin.zone, rec.destination.zone)
        count, km = movements[key]
        movements[key] = (count + 1, km + rec.distance_km)
    result.update({
        "run_id": run_id,
        "seed": seed,
        "fleet_size": fleet_size,
        "target_date": dataset.target_date.isoformat(),
        "cutoff": cutoff.isoformat(),
        "training_days": forecast.training_days,
        "forecast_hour": forecast.hour,
        "forecast_expected_by_zone": forecast.expected_by_zone,
        "forecast_absolute_error_by_zone": forecast_error(forecast, dataset.evaluation),
        "plan": {
            "recommendation_count": len(plan.recommendations),
            "applied_recommendation_count": len(applied),
            "adherence_hypothetical": adherence,
            "estimated_reposition_km": round(plan.reposition_km, 6),
            "projected_pickup_km": round(plan.projected_pickup_km, 6),
            "projected_coverage": plan.projected_coverage,
            "objective": plan.objective,
            "recommendations_aggregated": [
                {"from_zone": origin, "to_zone": destination, "count": count, "estimated_km": round(km, 6)}
                for (origin, destination), (count, km) in sorted(movements.items())
            ],
        },
        "gates": {
            "A_data_synthetic": True,
            "B_metric_synthetic": True,
            "C_availability_synthetic": True,
            "D_baseline_synthetic": True,
            "E_comparability_synthetic": result["comparable_inputs"],
            "F_reproducibility_synthetic": True,
            "A_to_F_real": False,
        },
    })
    return result


def run_synthetic(
    seed: int = 20261014,
    fleet_size: int = 5,
    minimum_coverage: float = 0.75,
    *,
    leste_train_count: int = 3,
    leste_eval_count: int = 3,
    initial_distribution: str = "center",
    max_reposition_km: float = 12,
    adherence: float = 1.0,
) -> dict[str, object]:
    dataset = make_synthetic(
        seed=seed, fleet_size=fleet_size,
        leste_train_count=leste_train_count, leste_eval_count=leste_eval_count,
        initial_distribution=initial_distribution,
    )
    return run_dataset(dataset, minimum_coverage, max_reposition_km=max_reposition_km, adherence=adherence)


def run_periods(seed: int = 20261014, *, periods: int = 3) -> dict[str, object]:
    """Avalia dias consecutivos com 28 dias anteriores independentes por corte."""
    if periods < 1:
        raise ValueError("número de períodos inválido")
    first_day = date(2026, 10, 15)
    runs = [
        run_dataset(make_synthetic(seed=seed + offset, target_date=first_day + timedelta(days=offset)))
        for offset in range(periods)
    ]
    baseline_km = sum(float(run["baseline"]["estimated_km_dead_total"]) for run in runs)
    proposed_km = sum(float(run["proposed"]["estimated_km_dead_total"]) for run in runs)
    baseline_served = sum(int(run["baseline"]["served"]) for run in runs)
    proposed_served = sum(int(run["proposed"]["served"]) for run in runs)
    return {
        "periods": [{
            "date": run["target_date"],
            "run_id": run["run_id"],
            "seed": run["seed"],
            "baseline_estimated_km": run["baseline"]["estimated_km_dead_total"],
            "proposed_estimated_km": run["proposed"]["estimated_km_dead_total"],
            "baseline_served": run["baseline"]["served"],
            "proposed_served": run["proposed"]["served"],
            "comparable_inputs": run["comparable_inputs"],
        } for run in runs],
        "baseline_estimated_km_total": round(baseline_km, 6),
        "proposed_estimated_km_total": round(proposed_km, 6),
        "baseline_served_total": baseline_served,
        "proposed_served_total": proposed_served,
        "estimated_km_reduction_percent": round(100 * (baseline_km - proposed_km) / baseline_km, 6) if baseline_km > 0 and all(run["comparable_inputs"] for run in runs) and proposed_served >= baseline_served else None,
    }


def sensitivity(seed: int = 20261014) -> list[dict[str, object]]:
    rows = []
    factors = {
        "fleet_size": (3, 5, 7),
        "minimum_coverage": (0.5, 0.75, 1.0),
        "leste_train_count": (1, 3, 4),
        "leste_eval_count": (1, 3, 4),
        "initial_distribution": ("center", "spread"),
        "max_reposition_km": (0, 5, 12),
        "adherence": (0.0, 0.5, 1.0),
    }
    for factor, values in factors.items():
        for value in values:
            run = run_synthetic(seed=seed, **{factor: value})
            rows.append({
                "factor": factor,
                "value": value,
                "estimated_km_reduction_percent": run["estimated_km_reduction_percent"],
                "baseline_pickup_km": run["baseline"]["estimated_pickup_km"],
                "proposed_pickup_km": run["proposed"]["estimated_pickup_km"],
                "proposed_reposition_km": run["proposed"]["estimated_reposition_km"],
                "actual_simulated_coverage": run["proposed"]["coverage"],
                "coverage_constraint_met": run["coverage_constraint_met"],
            })
    return rows


def _svg_bars(result: dict[str, object]) -> str:
    baseline = result["baseline"]
    proposed = result["proposed"]
    values = [float(baseline["estimated_km_dead_total"]), float(proposed["estimated_km_dead_total"])]
    maximum = max(values + [1.0])
    widths = [round(420 * value / maximum, 2) for value in values]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="650" height="220" viewBox="0 0 650 220" role="img" aria-label="Comparação sintética de KM vazio geodésico estimado">
<rect width="650" height="220" fill="white"/><text x="20" y="28" font-family="sans-serif" font-size="17">KM vazio estimado — cenário sintético</text>
<text x="20" y="74" font-family="sans-serif" font-size="13">Baseline</text><rect x="165" y="55" width="{widths[0]}" height="28" fill="#356899"/><text x="{175+widths[0]}" y="74" font-family="sans-serif" font-size="13">{values[0]:.2f} km</text>
<text x="20" y="124" font-family="sans-serif" font-size="13">Preventivo</text><rect x="165" y="105" width="{widths[1]}" height="28" fill="#2b8668"/><text x="{175+widths[1]}" y="124" font-family="sans-serif" font-size="13">{values[1]:.2f} km</text>
<text x="20" y="177" font-family="sans-serif" font-size="12">Inclui pickup e reposicionamento; Haversine não é rodagem observada.</text>
<text x="20" y="198" font-family="sans-serif" font-size="12">Cobertura: {baseline['coverage']:.1%} → {proposed['coverage']:.1%}. Sem inferência operacional.</text></svg>'''


def write_report(result: dict[str, object], directory: str | Path, *, include_sensitivity: bool = True) -> tuple[Path, Path]:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    payload = dict(result)
    if include_sensitivity:
        payload["sensitivity"] = sensitivity(seed=int(result["seed"]))
        payload["multiple_periods"] = run_periods(seed=int(result["seed"]))
    json_path = root / "synthetic_run.json"
    svg_path = root / "synthetic_comparison.svg"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    svg_path.write_text(_svg_bars(result), encoding="utf-8")
    return json_path, svg_path
