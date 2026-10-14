from tcc_frota.ingestion.pipeline import build_local_medallion
from tcc_frota.synthetic.generator import make_synthetic


def test_medallion_idempotent_and_no_real_data(tmp_path):
    dataset = make_synthetic(seed=9)
    first = build_local_medallion(dataset, tmp_path)
    second = build_local_medallion(dataset, tmp_path)
    assert first == second
    assert first["silver_requests"] == first["bronze_requests"]
    assert first["silver_vehicles"] == first["bronze_vehicles"]
    assert first["excluded"] == {}
    assert first["dataset_kind"] == "synthetic"
    assert (tmp_path / "gold" / "demand.csv").is_file()
