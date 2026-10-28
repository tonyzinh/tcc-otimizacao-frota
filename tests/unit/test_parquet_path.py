import pytest

from tcc_frota.ingestion.parquet import volume_parquet_path


def test_parquet_volume_path_requires_specific_file_or_directory():
    value = "/Volumes/workspace/tcc_frota/inputs/pedidos.parquet"
    assert volume_parquet_path(value) == value
    assert volume_parquet_path("/Volumes/workspace/tcc_frota/inputs/pedidos")


@pytest.mark.parametrize(
    "value",
    [
        "",
        "/Volumes/workspace/tcc_frota/inputs",
        "data/pedidos.parquet",
        "/Volumes/workspace/tcc_frota/inputs/../private.parquet",
        "/Volumes/workspace/tcc_frota/inputs//pedidos.parquet",
        "/Volumes/workspace/tcc_frota/inputs/*.parquet",
        "/Volumes/workspace;DROP/tcc_frota/inputs/pedidos.parquet",
    ],
)
def test_parquet_volume_path_rejects_ambiguous_sources(value):
    with pytest.raises(ValueError):
        volume_parquet_path(value)
