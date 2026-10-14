# Databricks notebook source
# 02: importa CSV sintético do Volume para Delta Bronze.
import sys
from pathlib import Path

for name, default in (("project_root", ""), ("catalog", "workspace"), ("schema", "tcc_frota_synthetic"), ("volume", "inputs"), ("pipeline_run_id", "synthetic_20261014")):
    dbutils.widgets.text(name, default)
root = dbutils.widgets.get("project_root")
if not root:
    raise ValueError("Informe project_root")
sys.path.insert(0, str(Path(root) / "src"))

from tcc_frota.spark_adapter import bronze_synthetic

catalog, schema, volume = (dbutils.widgets.get(name) for name in ("catalog", "schema", "volume"))
volume_path = f"/Volumes/{catalog}/{schema}/{volume}"
counts = bronze_synthetic(spark, volume_path, catalog, schema, dbutils.widgets.get("pipeline_run_id"))
print({"dataset_kind": "synthetic", "bronze_counts": counts})
