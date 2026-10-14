# Databricks notebook source
# 05: previsão D+1 a partir da Silver sintética, com corte anterior ao dia alvo.
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
from tcc_frota.spark_adapter import _write_run, fqtn, load_synthetic_silver

catalog, schema, run_id = (dbutils.widgets.get(name) for name in ("catalog", "schema", "pipeline_run_id"))
target = datetime.fromisoformat(dbutils.widgets.get("target_date")).date()
dataset = load_synthetic_silver(spark, catalog, schema, run_id, int(dbutils.widgets.get("seed")), target)
cutoff = datetime.combine(target - timedelta(days=1), time(20), tzinfo=timezone.utc)
prediction = forecast_hour(dataset.historical, dataset.zones, target, 8, cutoff)
rows = [(zone, 8, float(value), cutoff.isoformat()) for zone, value in prediction.expected_by_zone.items()]
df = spark.createDataFrame(rows, "zone string, hour int, expected double, cutoff string")
_write_run(df, fqtn(catalog, schema, "gold_forecast"), run_id)
print({"dataset_kind": "synthetic", "training_days": prediction.training_days, "zones": len(rows)})
