"""As figuras do artigo são cópias exatas da origem oficial em reports/figures."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _module():
    spec = importlib.util.spec_from_file_location("sync_article_figures", ROOT / "scripts" / "sync_article_figures.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_article_figures_match_official_source_when_checked():
    mod = _module()

    problems = mod.check()

    assert mod.referenced(), "o artigo deveria incluir ao menos uma figura"
    assert problems == []
