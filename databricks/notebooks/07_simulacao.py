# Databricks notebook source
# 07: replay dos mesmos pedidos/frota a partir da Silver; resultado contrafactual sintético.
import sys
from datetime import datetime
from pathlib import Path

for name, default in (("project_root", ""), ("catalog", "workspace"), ("schema", "tcc_frota_synthetic"), ("pipeline_run_id", "synthetic_20261014"), ("seed", "20261014"), ("target_date", "2026-10-15")):
    dbutils.widgets.text(name, default)
root = dbutils.widgets.get("project_root")
if not root:
    raise ValueError("Informe project_root")
sys.path.insert(0, str(Path(root) / "src"))

from tcc_frota.experiment import run_dataset
from tcc_frota.spark_adapter import _write_run, fqtn, load_synthetic_silver
from pyspark.sql import functions as F

catalog, schema, run_id = (dbutils.widgets.get(name) for name in ("catalog", "schema", "pipeline_run_id"))
target = datetime.fromisoformat(dbutils.widgets.get("target_date")).date()
dataset = load_synthetic_silver(spark, catalog, schema, run_id, int(dbutils.widgets.get("seed")), target)
result = run_dataset(dataset)
stored = spark.table(fqtn(catalog, schema, "gold_recommendations")).filter(F.col("run_id") == run_id).count()
if stored != result["plan"]["recommendation_count"]:
    raise ValueError("plano Gold e replay divergem; execute 06 com os mesmos parâmetros")
rows = [(part["scenario"], float(part["estimated_pickup_km"]), float(part["estimated_reposition_km"]), float(part["estimated_km_dead_total"]), float(part["coverage"] or 0), int(part["served"]), int(part["requests"])) for part in (result["baseline"], result["proposed"])]
df = spark.createDataFrame(rows, "scenario string, pickup_km double, reposition_km double, total_km double, coverage double, served int, requests int")
_write_run(df, fqtn(catalog, schema, "gold_metrics"), run_id)
print({"dataset_kind": "synthetic", "run_id": result["run_id"], "estimated_km_reduction_percent": result["estimated_km_reduction_percent"], "coverage_constraint_met": result["coverage_constraint_met"]})
