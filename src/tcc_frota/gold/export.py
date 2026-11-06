"""Cópia local mínima das tabelas Gold para o experimento Python.

As colunas são restritas ao necessário. O cache fica em `reports/runs/`, ignorado pelo
Git; contém dados pseudonimizados por corrida e não deve ser compartilhado.
"""

from __future__ import annotations

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


def read_table(cache_dir: str | Path, table: str) -> list[dict[str, object]]:
    authorize("real", "local")
    import pyarrow.parquet as pq

    return pq.read_table(Path(cache_dir) / f"{table}.parquet").to_pylist()
