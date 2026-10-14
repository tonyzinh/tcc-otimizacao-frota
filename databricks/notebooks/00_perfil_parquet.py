# Databricks notebook source
# Inspeção somente de esquema; não mostra linhas nem faz upload do arquivo.
import sys
from pathlib import Path

dbutils.widgets.text("project_root", "")
dbutils.widgets.text("parquet_path", "")
dbutils.widgets.dropdown("real_data_authorized", "false", ["false", "true"])
dbutils.widgets.dropdown("count_rows", "false", ["false", "true"])

if dbutils.widgets.get("real_data_authorized") != "true":
    raise PermissionError("confirme a autorização específica para este arquivo e workspace")
root = Path(dbutils.widgets.get("project_root"))
if not str(root).startswith("/Workspace/") or not (root / "src" / "tcc_frota").is_dir():
    raise ValueError("project_root deve apontar ao Git folder em /Workspace")
sys.path.insert(0, str(root / "src"))

from tcc_frota.ingestion.parquet import volume_parquet_path

source = volume_parquet_path(dbutils.widgets.get("parquet_path"))
frame = spark.read.format("parquet").load(source)
print({
    "source_format": "parquet",
    "columns_and_types": [(field.name, field.dataType.simpleString()) for field in frame.schema.fields],
    "row_count": frame.count() if dbutils.widgets.get("count_rows") == "true" else "not_counted",
    "rows_displayed": 0,
})
