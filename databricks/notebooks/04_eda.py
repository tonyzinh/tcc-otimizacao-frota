# Databricks notebook source
# 04: cria Gold de contagens por zona/hora/split, sem trajetórias individuais.
import sys
from pathlib import Path

for name, default in (("project_root", ""), ("catalog", "workspace"), ("schema", "tcc_frota_synthetic"), ("pipeline_run_id", "synthetic_20261014")):
    dbutils.widgets.text(name, default)
root = dbutils.widgets.get("project_root")
if not root:
    raise ValueError("Informe project_root")
sys.path.insert(0, str(Path(root) / "src"))

from tcc_frota.spark_adapter import gold_demand_synthetic

catalog, schema, run_id = (dbutils.widgets.get(name) for name in ("catalog", "schema", "pipeline_run_id"))
print({"gold_cells": gold_demand_synthetic(spark, catalog, schema, run_id)})
