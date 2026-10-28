"""Impede que as respostas fictícias da operação (16/10/2026) voltem a documentos versionados.

Varre arquivos versionados em docs/, tabelas/ e todo *.md / *.tex; o próprio teste fica fora da busca.
"""

import subprocess
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
PHRASES = ("resposta simulada", "respostas simuladas", "equipe de operacoes e sistemas", "ficticia")


def _norm(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def _tracked() -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "docs", "tabelas", "*.md", "*.tex"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git indisponível")
    return [ROOT / p for p in sorted(set(out.splitlines())) if (ROOT / p).resolve() != SELF]


def test_no_fictitious_company_answers_in_versioned_docs():
    hits = []
    for path in _tracked():
        if not path.is_file():
            continue
        text = _norm(path.read_text(encoding="utf-8", errors="ignore"))
        hits += [f"{path.relative_to(ROOT)}: {p}" for p in PHRASES if p in text]
    assert not hits, "trechos proibidos: " + "; ".join(hits)
