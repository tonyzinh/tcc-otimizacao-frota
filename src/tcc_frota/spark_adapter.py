"""Adaptador Databricks opcional. Requer Spark do ambiente; nunca envia arquivos locais."""
from __future__ import annotations

import re
from datetime import date, timezone

from tcc_frota.models import Position, Request, Vehicle
from tcc_frota.synthetic.generator import SyntheticDataset


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError("identificador Unity Catalog inválido")
    return value


def fqtn(catalog: str, schema: str, name: str) -> str:
    return ".".join(_identifier(item) for item in (catalog, schema, name))


def setup_synthetic(spark, catalog: str, schema: str, volume: str) -> str:
    _identifier(catalog)
    _identifier(schema)
    _identifier(volume)
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog}.{schema}.{volume}")
    return f"/Volumes/{catalog}/{schema}/{volume}"


def _write_run(df, table: str, run_id: str) -> None:
    from pyspark.sql import functions as F

    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("run_id inválido")
    df.withColumn("run_id", F.lit(run_id)).write.format("delta").mode("overwrite").option(
        "replaceWhere", f"run_id = '{run_id}'"
    ).saveAsTable(table)


def bronze_synthetic(spark, volume_path: str, catalog: str, schema: str, run_id: str) -> dict[str, int]:
    from pyspark.sql import functions as F

    spark.conf.set("spark.sql.session.timeZone", "UTC")
    counts = {}
    for kind in ("requests", "vehicles"):
        df = spark.read.option("header", True).option("mode", "FAILFAST").csv(f"{volume_path}/{kind}.csv")
        if df.filter(F.col("dataset_kind") != "synthetic").limit(1).count():
            raise PermissionError("o notebook Bronze aceita somente dados sintéticos")
        counts[kind] = df.count()
        _write_run(df, fqtn(catalog, schema, f"bronze_{kind}"), run_id)
    return counts


def silver_synthetic(spark, catalog: str, schema: str, run_id: str) -> dict[str, int]:
    from pyspark.sql import functions as F

    spark.conf.set("spark.sql.session.timeZone", "UTC")
    requests = spark.table(fqtn(catalog, schema, "bronze_requests")).filter(F.col("run_id") == run_id)
    vehicles = spark.table(fqtn(catalog, schema, "bronze_vehicles")).filter(F.col("run_id") == run_id)
    if requests.groupBy("request_id").count().filter("count > 1").limit(1).count():
        raise ValueError("IDs duplicados no Bronze sintético")
    clean_requests = requests.select(
        "request_id", F.to_timestamp("created_at").alias("created_at"),
        F.col("origin_zone").alias("zone"), F.col("origin_lat").cast("double").alias("origin_lat"),
        F.col("origin_lon").cast("double").alias("origin_lon"), "destination_zone",
        F.col("destination_lat").cast("double").alias("destination_lat"),
        F.col("destination_lon").cast("double").alias("destination_lon"),
        F.col("trip_minutes").cast("double").alias("trip_minutes"), "split", "dataset_kind",
    )
    valid = (
        F.col("request_id").isNotNull() & F.col("created_at").isNotNull()
        & F.col("origin_lat").between(-90, 90) & F.col("origin_lon").between(-180, 180)
        & F.col("destination_lat").between(-90, 90) & F.col("destination_lon").between(-180, 180)
        & (F.col("trip_minutes") > 0) & F.col("split").isin("train", "test")
    )
    rejected = clean_requests.filter(~valid).count()
    clean_requests = clean_requests.filter(valid)
    clean_vehicles = vehicles.select(
        "vehicle_id", "zone", F.col("lat").cast("double").alias("lat"),
        F.col("lon").cast("double").alias("lon"),
        F.to_timestamp("available_from").alias("available_from"),
        F.to_timestamp("available_until").alias("available_until"), "dataset_kind",
    )
    if clean_vehicles.filter(F.col("vehicle_id").isNull() | F.col("lat").isNull() | F.col("lon").isNull()).limit(1).count():
        raise ValueError("veículo sintético inválido")
    _write_run(clean_requests, fqtn(catalog, schema, "silver_requests"), run_id)
    _write_run(clean_vehicles, fqtn(catalog, schema, "silver_vehicles"), run_id)
    return {"requests_valid": clean_requests.count(), "requests_excluded": rejected, "vehicles": clean_vehicles.count()}


def gold_demand_synthetic(spark, catalog: str, schema: str, run_id: str) -> int:
    from pyspark.sql import functions as F

    requests = spark.table(fqtn(catalog, schema, "silver_requests")).filter(F.col("run_id") == run_id)
    demand = requests.groupBy("split", "zone", F.hour("created_at").alias("hour")).agg(F.countDistinct("request_id").alias("request_count"))
    _write_run(demand, fqtn(catalog, schema, "gold_demand"), run_id)
    return demand.count()


def load_synthetic_silver(spark, catalog: str, schema: str, run_id: str, seed: int, target_date: date) -> SyntheticDataset:
    """Coleta limitada para o núcleo local; rejeita volume maior que 10 mil linhas."""
    from pyspark.sql import functions as F

    request_rows = spark.table(fqtn(catalog, schema, "silver_requests")).filter(F.col("run_id") == run_id).limit(10001).collect()
    vehicle_rows = spark.table(fqtn(catalog, schema, "silver_vehicles")).filter(F.col("run_id") == run_id).limit(10001).collect()
    if len(request_rows) > 10000 or len(vehicle_rows) > 10000:
        raise ValueError("coleta para o núcleo excede limite sintético; agregue no Spark")
    zones: dict[str, Position] = {}
    historical: list[Request] = []
    evaluation: list[Request] = []
    for row in request_rows:
        if row.dataset_kind != "synthetic":
            raise PermissionError("somente sintéticos")
        origin = Position(row.zone, row.origin_lat, row.origin_lon)
        dest = Position(row.destination_zone, row.destination_lat, row.destination_lon)
        zones.setdefault(origin.zone, origin)
        zones.setdefault(dest.zone, dest)
        request = Request(row.request_id, row.created_at.replace(tzinfo=timezone.utc) if row.created_at.tzinfo is None else row.created_at, origin, dest, row.trip_minutes)
        (historical if row.split == "train" else evaluation).append(request)
    vehicles: list[Vehicle] = []
    for row in vehicle_rows:
        if row.dataset_kind != "synthetic":
            raise PermissionError("somente sintéticos")
        position = Position(row.zone, row.lat, row.lon)
        zones.setdefault(position.zone, position)
        start = row.available_from.replace(tzinfo=timezone.utc) if row.available_from.tzinfo is None else row.available_from
        end = row.available_until.replace(tzinfo=timezone.utc) if row.available_until.tzinfo is None else row.available_until
        vehicles.append(Vehicle(row.vehicle_id, position, start, end))
    return SyntheticDataset(zones, historical, evaluation, vehicles, target_date, seed)
