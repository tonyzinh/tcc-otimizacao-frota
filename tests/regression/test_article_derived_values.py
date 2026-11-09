"""Os números derivados citados no artigo (antes calculados por scripts locais da rodada 6) saem dos dados por dia versionados."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _module():
    spec = importlib.util.spec_from_file_location("compute_article_derived_values", ROOT / "scripts" / "compute_article_derived_values.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_article_derived_values_match_daily_data_and_text_when_recomputed():
    mod = _module()

    rows = mod.compute()
    problems = mod.check(rows)

    assert len(rows) == 21
    assert problems == []
