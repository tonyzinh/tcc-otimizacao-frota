# Databricks notebook source
# 01: gera e audita apenas o conjunto sintético no volume gerenciado.
import sys
from pathlib import Path

dbutils.widgets.text("project_root", "")
dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "tcc_frota_synthetic")
dbutils.widgets.text("volume", "inputs")
dbutils.widgets.text("seed", "20261014")
root = dbutils.widgets.get("project_root")
if not root:
    raise ValueError("Informe project_root como caminho do Git folder em /Workspace")
sys.path.insert(0, str(Path(root) / "src"))

from tcc_frota.spark_adapter import setup_synthetic
from tcc_frota.synthetic.generator import export_synthetic, make_synthetic
from tcc_frota.ingestion.files import read_rows
from tcc_frota.quality.audit import audit_rows

volume_path = setup_synthetic(spark, dbutils.widgets.get("catalog"), dbutils.widgets.get("schema"), dbutils.widgets.get("volume"))
dataset = make_synthetic(seed=int(dbutils.widgets.get("seed")))
request_path, vehicle_path = export_synthetic(dataset, volume_path)
request_audit = audit_rows(read_rows(request_path), ("request_id", "created_at"), key="request_id")
vehicle_audit = audit_rows(read_rows(vehicle_path), ("vehicle_id",), key="vehicle_id")
print({"dataset_kind": "synthetic", "requests": request_audit.as_dict(), "vehicles": vehicle_audit.as_dict()})
