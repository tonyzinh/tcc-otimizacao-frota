import pytest

from tcc_frota.spark_adapter import fqtn


def test_unity_catalog_identifiers_are_validated_without_spark():
    assert fqtn("workspace", "tcc_frota_synthetic", "gold_metrics") == "workspace.tcc_frota_synthetic.gold_metrics"
    with pytest.raises(ValueError):
        fqtn("workspace; DROP TABLE x", "safe", "metrics")
