# Databricks notebook source
# 03: converte e valida entidades sintéticas, com contagem de exclusões.
import sys
from pathlib import Path

for name, default in (("project_root", ""), ("catalog", "workspace"), ("schema", "tcc_frota_synthetic"), ("pipeline_run_id", "synthetic_20261014")):
    dbutils.widgets.text(name, default)
root = dbutils.widgets.get("project_root")
if not root:
    raise ValueError("Informe project_root")
sys.path.insert(0, str(Path(root) / "src"))

from tcc_frota.spark_adapter import silver_synthetic

print(silver_synthetic(spark, dbutils.widgets.get("catalog"), dbutils.widgets.get("schema"), dbutils.widgets.get("pipeline_run_id")))
