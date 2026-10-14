# Databricks notebook source
# Auditoria agregada do Parquet autorizado. Não exibe registros nem identificadores.
import sys
from pathlib import Path

from pyspark.sql import functions as F

dbutils.widgets.text("project_root", "")
dbutils.widgets.text("parquet_path", "")
dbutils.widgets.dropdown("real_data_authorized", "false", ["false", "true"])

if dbutils.widgets.get("real_data_authorized") != "true":
    raise PermissionError("confirme a autorização específica para este arquivo e workspace")
root = Path(dbutils.widgets.get("project_root"))
if not str(root).startswith("/Workspace/") or not (root / "src" / "tcc_frota").is_dir():
    raise ValueError("project_root deve apontar ao Git folder em /Workspace")
sys.path.insert(0, str(root / "src"))

from tcc_frota.ingestion.parquet import volume_parquet_path

source = volume_parquet_path(dbutils.widgets.get("parquet_path"))
frame = spark.read.format("parquet").load(source)
required = {"CD_SOLICITACAO", "DT_REGISTRO", "TX_STATUS"}
missing = sorted(required - set(frame.columns))
if missing:
    raise ValueError(f"colunas fundamentais ausentes: {missing}")

total, unique, without_id = frame.agg(
    F.count("*").alias("total"),
    F.countDistinct("CD_SOLICITACAO").alias("unique"),
    F.coalesce(F.sum(F.col("CD_SOLICITACAO").isNull().cast("long")), F.lit(0)).alias("without_id"),
).first()
coverage_fields = [
    "CD_VEICULO", "DT_INICIO_REALIZADA", "DT_FIM_REALIZADA",
    "NU_DISTANCIA_ACEITE_CHEGUEI", "NU_DISTPERCORRIDA",
    "TX_ORIGEM_LAT", "TX_ORIGEM_LNG", "TX_DESTINOREAL_LAT", "TX_DESTINOREAL_LNG",
]
present = [name for name in coverage_fields if name in frame.columns]
coverage = frame.agg(*(F.count(name).alias(name) for name in present)).first().asDict()
known_statuses = [
    "AguardandoCondutor", "CondutorACaminho", "CondutorChegou",
    "CorridaIniciada", "CorridaEncerrada", "NaoAtendida", "LimiteEsperaAtingido",
]
classified_status = F.when(F.col("TX_STATUS").isin(known_statuses), F.col("TX_STATUS")).otherwise("other_or_null")
status_counts = {
    row["status_class"]: row["count"]
    for row in frame.groupBy(classified_status.alias("status_class")).count().collect()
}
print({
    "source_format": "parquet",
    "total_rows": total,
    "distinct_request_ids": unique,
    "missing_request_ids": without_id,
    "repeated_request_rows": total - unique - without_id,
    "non_null_by_field": coverage,
    "status_counts": status_counts,
    "timestamp_semantics": "unverified",
    "timezone": "unverified",
    "vehicle_availability": "not_established_by_this_audit",
    "rows_displayed": 0,
})
