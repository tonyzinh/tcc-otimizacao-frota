import json
from datetime import date, datetime

import pytest

from tcc_frota.demand.forecast import forecast_temporal_counts
from tcc_frota.ingestion.elasticsearch import discover, iter_jsonl, process_local, validate_manifest
from tcc_frota.ingestion.es_analytics import SUMMARY_COUNTS, build_analytics


def month(root, dataset, name, rows, *, status="completed", declared=None):
    directory = root / dataset / name
    directory.mkdir(parents=True)
    (directory / "manifest.json").write_text(json.dumps({"status": status, "dataset": dataset,
        "month": name, "region": 1, "documents": len(rows) if declared is None else declared}), encoding="utf-8")
    (directory / "dados.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    (directory / "pagina_0001.json").write_text(json.dumps(rows), encoding="utf-8")
    return directory


def test_manifest_jsonl_and_incomplete_month(tmp_path):
    root = tmp_path / "raw"
    good = month(root, "solicitacoes", "2025-10", [{"codigo": 1}])
    month(root, "ofertas", "2025-10", [{"codigo": "x"}], status="running")
    assert validate_manifest(good / "manifest.json", "solicitacoes", "2025-10") == (True, "complete", 1)
    assert next(row for row in discover(root) if row["dataset"] == "ofertas" and row["month"] == "2025-10")["status"] == "manifest_not_complete"
    assert list(iter_jsonl(good / "dados.jsonl")) == [(1, {"codigo": 1})]
    (good / "dados.jsonl").write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="não é objeto"):
        list(iter_jsonl(good / "dados.jsonl"))


def test_count_mismatch_is_excluded_from_analytics(tmp_path, monkeypatch):
    pytest.importorskip("pyarrow")
    monkeypatch.setenv("TCC_REAL_DATA_AUTHORIZED", "YES")
    root = tmp_path / "raw"
    month(root, "sumarios", "2025-10", [{"codigo": "one"}], declared=2)
    report = process_local(root, tmp_path / "runs")
    row = next(item for item in report["coverage"] if item["dataset"] == "sumarios" and item["month"] == "2025-10")
    assert row["status"] == "count_mismatch"
    result = build_analytics(tmp_path / "runs" / report["run_id"])
    assert result["audit"].get("summary_documents", 0) == 0


def test_local_layers_dedup_temporal_only_and_no_invented_fleet(tmp_path, monkeypatch):
    pytest.importorskip("pyarrow")
    monkeypatch.setenv("TCC_REAL_DATA_AUTHORIZED", "YES")
    root = tmp_path / "raw"
    event = {"dT_REGISTRO": "2026-01-05T08:00:00-03:00", "tX_STATUS": "Criada"}
    request = {"codigo": 7, "dT_REGISTRO": "2026-01-07T12:00:00-03:00",
               "tX_STATUS": "Encerrada", "logStatus": [event]}
    month(root, "solicitacoes", "2026-01", [request, {**request, "tX_STATUS": "Outro"},
        {"codigo": 8, "logStatus": []}])
    month(root, "solicitacoes", "2026-02", [{**request, "dT_REGISTRO": "2026-02-01T10:00:00-03:00"}])
    summary = {"dataHora": "2026-01-05T08:00:00-03:00", "codigoRegiao": 1,
               **{field: 1 for field in SUMMARY_COUNTS}}
    month(root, "sumarios", "2026-01", [summary])
    offer = {"dataHora": "2026-01-05T10:30:00-03:00", "ofertaList": [
        {"status": "Online", "latitude": -20.3, "longitude": -40.3,
         "dataPosicaoGPS": "2026-01-05T08:00:00-03:00"}, {"status": "mystery"}]}
    month(root, "ofertas", "2026-01", [offer])
    month(root, "ofertas", "2026-02", [{"dataHora": "2026-02-01T12:00:00-03:00"}], status="running")
    report = process_local(root, tmp_path / "runs")
    assert report["coverage"][0]["status"] in {"month_missing", "ready"}
    run = tmp_path / "runs" / report["run_id"]
    assert not (run / "silver" / "ofertas" / "2026-02").exists()
    assert build_analytics(run)["demand_status"] == "blocked_creation_semantics"
    result = build_analytics(run, creation_status="Criada")
    assert result["audit"]["unique_requests_with_creation"] == 1
    assert result["audit"]["duplicate_request_documents"] == 2
    assert result["audit"]["offer_position_over_120_min"] == 1
    assert result["eligible_fleet_status"] == "blocked_unverified"
    import pyarrow.parquet as pq
    gold = pq.read_table(run / "gold" / "demand_hourly.parquet").to_pylist()
    assert len(gold) == 1 and gold[0]["request_count"] == 1 and gold[0]["hour"] == 8
    assert gold[0]["spatial_status"] == "origin_unavailable"
    assert pq.read_table(run / "gold" / "online_hourly.parquet").to_pylist()[0]["online_is_free"] is False
    with pytest.raises(ValueError, match="dT_REGISTRO"):
        build_analytics(run, creation_field="dT_REGISTRO")


def test_forecast_uses_only_complete_days_before_cutoff():
    past = [(date(2026, 1, 5), 8, 2), (date(2026, 1, 12), 8, 4)]
    future = [(date(2026, 1, 19), 8, 1000), (date(2026, 1, 20), 8, 1000)]
    cutoff = datetime.fromisoformat("2026-01-19T20:00:00-03:00")
    first = forecast_temporal_counts(past, ["2026-01"], date(2026, 1, 20), cutoff)
    second = forecast_temporal_counts(past + future, ["2026-01"], date(2026, 1, 20), cutoff)
    assert first == second
    assert first["expected_by_hour"]["8"] < 1000
    with pytest.raises(ValueError):
        forecast_temporal_counts(past, ["2026-01"], date(2026, 1, 19), cutoff)
