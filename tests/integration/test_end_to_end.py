import json

from tcc_frota.experiment import run_periods, run_synthetic, write_report
from tcc_frota.ingestion.files import read_rows
from tcc_frota.quality.audit import audit_rows
from tcc_frota.synthetic.generator import export_synthetic, make_synthetic


def test_synthetic_pipeline_reproducible_and_aggregated(tmp_path):
    dataset = make_synthetic(seed=123)
    requests, vehicles = export_synthetic(dataset, tmp_path / "data")
    rows = list(read_rows(requests))
    assert rows and all(row["dataset_kind"] == "synthetic" for row in rows)
    assert audit_rows(rows, ("request_id", "created_at"), key="request_id").duplicate_keys == 0
    assert list(read_rows(vehicles))
    first = run_synthetic(seed=123)
    second = run_synthetic(seed=123)
    assert first == second
    assert first["comparable_inputs"]
    assert first["gates"]["A_to_F_real"] is False
    assert first["baseline"]["observed_km"] is None
    assert first["proposed"]["estimated_km_dead_total"] == round(
        first["proposed"]["estimated_pickup_km"] + first["proposed"]["estimated_reposition_km"], 6
    )
    report, chart = write_report(first, tmp_path / "reports", include_sensitivity=False)
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["run_id"] == first["run_id"]
    assert "Haversine" in chart.read_text(encoding="utf-8")


def test_empty_fleet_does_not_claim_reduction():
    result = run_synthetic(seed=123, fleet_size=0)
    assert result["baseline"]["served"] == 0
    assert result["proposed"]["served"] == 0
    assert result["estimated_km_reduction_percent"] is None


def test_multiple_synthetic_periods_have_independent_d1_cutoffs():
    result = run_periods(seed=123, periods=3)
    assert [period["date"] for period in result["periods"]] == ["2026-10-15", "2026-10-16", "2026-10-17"]
    assert all(period["comparable_inputs"] for period in result["periods"])
    assert result == run_periods(seed=123, periods=3)
    assert result["baseline_served_total"] == result["proposed_served_total"] == 30
    assert result["estimated_km_reduction_percent"] == 0.0
