"""Cópia local mínima das tabelas Gold para o experimento Python.

As colunas são restritas ao necessário. O cache fica em `reports/runs/`, ignorado pelo
Git; contém dados pseudonimizados por corrida e não deve ser compartilhado.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from tcc_frota.ingestion.files import authorize

GOLD = "cat_mobilidade_urbana_gold.db_frota"

TABLES: dict[str, tuple[str, ...]] = {
    "tb_dim_zonas_h3": ("h3_r8", "h3_r7", "lat_centro_r7", "lon_centro_r7"),
    "tb_demanda_zona_hora": ("data_local", "hora_local", "tipo_solicitacao", "h3_r7", "qtd_corridas_atendidas"),
    "tb_frota_sessoes": (
        "id_motorista_pseud",
        "seq_sessao",
        "estado_sessao",
        "ts_inicio",
        "ts_fim",
        "lat_inicio",
        "lon_inicio",
        "h3_r8_inicio",
    ),
    "tb_frota_motorista_hora": (
        "id_motorista_pseud",
        "data_local",
        "hora_local",
        "fl_disponivel_na_hora",
        "lat_primeira",
        "lon_primeira",
        "h3_r8_primeira",
    ),
    "tb_corridas_replay": (
        "id_corrida",
        "id_motorista_pseud",
        "tipo_solicitacao",
        "ts_registro",
        "ts_aceite",
        "ts_chegada",
        "ts_inicio",
        "ts_fim",
        "data_local",
        "lat_origem",
        "lon_origem",
        "h3_r7_origem",
        "lat_destino",
        "lon_destino",
        "h3_r7_destino",
        "km_pickup_reta",
        "km_gps_pickup",
        "min_viagem",
    ),
    "tb_km_vazio_segmentos": (
        "id_corrida",
        "data_local",
        "fl_segmento_valido",
        "km_reta_fim_ate_origem",
        "km_reta_aceite_ate_origem",
        "km_gps_ocioso",
        "km_gps_pickup_nao_concluido",
        "km_gps_pickup",
        "km_gps_vazio_total",
    ),
}


def export_gold(spark, out_dir: str | Path, *, catalog_schema: str = GOLD) -> dict[str, object]:
    """Grava cada tabela Gold como Parquet local e retorna um manifesto agregado."""
    authorize("real", "local")
    import pyarrow as pa
    import pyarrow.parquet as pq

    out = Path(out_dir)
    if "runs" not in out.resolve().parts:
        raise PermissionError("o cache da Gold real deve ficar em reports/runs/, ignorado pelo Git")
    out.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {"source": catalog_schema, "exported_at": datetime.now(UTC).isoformat(), "tables": {}}
    for table, columns in TABLES.items():
        frame = spark.table(f"{catalog_schema}.{table}").select(*columns)
        arrow = frame.toArrow() if hasattr(frame, "toArrow") else pa.Table.from_pandas(frame.toPandas())
        pq.write_table(arrow, out / f"{table}.parquet")
        manifest["tables"][table] = {"rows": arrow.num_rows, "columns": list(columns)}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def read_table(cache_dir: str | Path, table: str) -> list[dict[str, object]]:
    authorize("real", "local")
    import pyarrow.parquet as pq

    return pq.read_table(Path(cache_dir) / f"{table}.parquet").to_pylist()


TABLES_V2 = (
    "tb_gld_replay_pedidos_v2",
    "tb_gld_demanda_zona_hora_v2",
    "tb_gld_frota_snapshot_v2",
    "tb_gld_frota_sessoes_v2",
    "tb_gld_frota_motorista_hora_v2",
    "tb_gld_calibracao_v2",
    "tb_gld_km_vazio_v2",
    "tb_gld_qualidade_v2",
)


def export_gold_v2(spark, out_dir: str | Path, *, catalog_schema: str = GOLD) -> dict[str, object]:
    """Exporta as Gold v2 inteiras (já pseudonimizadas e com coordenadas de passageiro arredondadas)."""
    authorize("real", "local")
    import pyarrow as pa
    import pyarrow.parquet as pq

    out = Path(out_dir)
    if "runs" not in out.resolve().parts:
        raise PermissionError("o cache da Gold real deve ficar em reports/runs/, ignorado pelo Git")
    out.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {"source": catalog_schema, "exported_at": datetime.now(UTC).isoformat(), "tables": {}}
    for table in TABLES_V2:
        frame = spark.table(f"{catalog_schema}.{table}")
        arrow = frame.toArrow() if hasattr(frame, "toArrow") else pa.Table.from_pandas(frame.toPandas())
        pq.write_table(arrow, out / f"{table}.parquet")
        manifest["tables"][table] = {"rows": arrow.num_rows, "columns": arrow.column_names}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest
