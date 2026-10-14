# Databricks notebook source
# 06: plano preventivo sintético congelado antes dos pedidos do dia alvo.
import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

for name, default in (("project_root", ""), ("catalog", "workspace"), ("schema", "tcc_frota_synthetic"), ("pipeline_run_id", "synthetic_20261014"), ("seed", "20261014"), ("target_date", "2026-10-15")):
    dbutils.widgets.text(name, default)
root = dbutils.widgets.get("project_root")
if not root:
    raise ValueError("Informe project_root")
sys.path.insert(0, str(Path(root) / "src"))

from tcc_frota.demand.forecast import forecast_hour
from tcc_frota.optimization.greedy import greedy_plan
from tcc_frota.spark_adapter import _write_run, fqtn, load_synthetic_silver

catalog, schema, run_id = (dbutils.widgets.get(name) for name in ("catalog", "schema", "pipeline_run_id"))
target = datetime.fromisoformat(dbutils.widgets.get("target_date")).date()
dataset = load_synthetic_silver(spark, catalog, schema, run_id, int(dbutils.widgets.get("seed")), target)
cutoff = datetime.combine(target - timedelta(days=1), time(20), tzinfo=timezone.utc)
forecast = forecast_hour(dataset.historical, dataset.zones, target, 8, cutoff)
start = datetime.combine(target, time(7), tzinfo=timezone.utc)
plan = greedy_plan(dataset.vehicles, dataset.zones, forecast.expected_by_zone, start, min_coverage=0.75, max_reposition_km=12)
rows = [(r.vehicle_id, r.origin.zone, r.destination.zone, r.start_at.isoformat(), float(r.distance_km)) for r in plan.recommendations]
df = spark.createDataFrame(rows, "vehicle_id string, origin_zone string, destination_zone string, start_at string, estimated_km double")
_write_run(df, fqtn(catalog, schema, "gold_recommendations"), run_id)
availability = [
    (vehicle.vehicle_id, vehicle.position.zone if vehicle.position else None, vehicle.available_from.isoformat(), vehicle.available_until.isoformat(), bool(vehicle.active and vehicle.driver_ready and vehicle.position is not None))
    for vehicle in dataset.vehicles
]
availability_df = spark.createDataFrame(availability, "vehicle_id string, initial_zone string, available_from string, available_until string, eligible boolean")
_write_run(availability_df, fqtn(catalog, schema, "gold_availability_planned"), run_id)
print({"dataset_kind": "synthetic", "recommendations": len(rows), "estimated_reposition_km": plan.reposition_km})
