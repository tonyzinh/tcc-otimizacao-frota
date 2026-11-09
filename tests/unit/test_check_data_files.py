"""O gancho de pré-commit bloqueia dados, segredos e arquivos grandes, e deixa passar código e agregados."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _module():
    spec = importlib.util.spec_from_file_location("check_data_files", ROOT / "scripts" / "check_data_files.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_problems_blocks_data_and_secrets_when_paths_are_sensitive():
    mod = _module()

    found = mod.problems(
        ["data/raw/v1_viagens/x/manifest.json", "reports/a/dia=2026-10-01.parquet", ".env", "configs/private/custos.yaml", "a.salt"]
    )

    assert len(found) == 5


def test_problems_allows_code_aggregates_and_env_example_when_paths_are_safe():
    mod = _module()

    found = mod.problems(
        ["src/tcc_frota/domain/entities.py", "reports/historical/frozen_evaluation/analise/final_absolutos.csv", ".env.example"]
    )

    assert found == []


def test_problems_blocks_large_file_when_size_exceeds_limit(tmp_path):
    mod = _module()
    big = tmp_path / "grande.csv"
    big.write_bytes(b"0" * (mod.MAX_BYTES + 1))

    found = mod.problems([str(big)])

    assert len(found) == 1 and "bytes" in found[0]
