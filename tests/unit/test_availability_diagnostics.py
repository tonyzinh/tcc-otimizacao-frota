import csv
from datetime import date

import pytest

from tcc_frota.availability.contracts import SourceContract, inventory
from tcc_frota.availability.diagnostics import diagnose_source


def test_inventory_detects_csv_and_missing_parquet(tmp_path):
    (tmp_path / "CORRIDAS_V1.csv").write_text("CD_SOLICITACAO\n", encoding="utf-8")
    rows = {item["dataset"]: item for item in inventory(tmp_path)}
    assert rows["corridas_v1"]["formats"] == ["csv"]
    assert rows["cobli_eventos"]["status"] == "AUSENTE"


def test_diagnostic_reports_coverage_duplicates_and_bad_dates_without_values(tmp_path):
    path = tmp_path / "corridas_v1.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["CD_SOLICITACAO", "DT_REGISTRO", "TX_STATUS"])
        writer.writeheader()
        writer.writerows(
            [
                {"CD_SOLICITACAO": "private-1", "DT_REGISTRO": "2025-01-01 10:00:00", "TX_STATUS": "CorridaEncerrada"},
                {"CD_SOLICITACAO": "private-1", "DT_REGISTRO": "bad-time", "TX_STATUS": "CorridaEncerrada"},
                {"CD_SOLICITACAO": "", "DT_REGISTRO": "2024-12-31 23:00:00", "TX_STATUS": ""},
            ]
        )
    contract = SourceContract("corridas_v1", ("CD_SOLICITACAO", "DT_REGISTRO"), ("DT_REGISTRO",), "CD_SOLICITACAO")
    report = diagnose_source(tmp_path, contract, timezone="America/Sao_Paulo", period_start=date(2025, 1, 1))
    assert report["rows"] == 3
    assert report["duplicate_key_rows"] == 1
    assert report["missing_key_rows"] == 1
    assert report["invalid_timestamp_by_field"] == {"DT_REGISTRO": 1}
    assert report["outside_requested_period_by_primary_time"] == 1
    assert "private-1" not in str(report)


def test_null_marker_is_missing_not_invalid_timestamp(tmp_path):
    path = tmp_path / "corridas_v1.csv"
    path.write_text("CD_SOLICITACAO,DT_REGISTRO\nr1,NaT\nr2,NULL\n", encoding="utf-8")
    contract = SourceContract("corridas_v1", ("CD_SOLICITACAO", "DT_REGISTRO"), ("DT_REGISTRO",), "CD_SOLICITACAO")
    report = diagnose_source(tmp_path, contract, timezone="America/Sao_Paulo")
    assert report["invalid_timestamp_by_field"] == {}
    assert report["non_null_by_required_or_time_field"] == {"CD_SOLICITACAO": 2}


def test_partitioned_parquet_is_streamed_when_pyarrow_is_installed(tmp_path):
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    for month in ("01", "02"):
        directory = tmp_path / "corridas_v1" / "year=2025" / f"month={month}"
        directory.mkdir(parents=True)
        pq.write_table(
            pa.table({"CD_SOLICITACAO": [f"r{month}"], "DT_REGISTRO": [f"2025-{month}-01 10:00:00"]}), directory / "part.parquet"
        )
    contract = SourceContract("corridas_v1", ("CD_SOLICITACAO", "DT_REGISTRO"), ("DT_REGISTRO",), "CD_SOLICITACAO")
    report = diagnose_source(tmp_path, contract, timezone="America/Sao_Paulo")
    assert report["rows"] == 2
    assert report["files"] == 2
    assert report["formats"] == ["parquet"]
