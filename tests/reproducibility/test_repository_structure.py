"""Estrutura do repositório reorganizado: pastas obrigatórias, um único `notebook/`, sem caminhos absolutos de autores."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ("domain", "data", "assignment", "simulation", "scenarios", "metrics", "visualization", "cli")


def test_source_packages_exist_when_layout_is_reorganized():
    for pkg in PACKAGES:
        assert (ROOT / "src" / "tcc_frota" / pkg / "__init__.py").exists(), pkg


def test_single_notebook_folder_has_five_named_notebooks():
    names = sorted(p.name for p in (ROOT / "notebook").glob("*.ipynb"))
    assert names == [
        "01_data_overview.ipynb",
        "02_hungarian_example.ipynb",
        "03_greater_vitoria_h3.ipynb",
        "04_historical_results.ipynb",
        "05_synthetic_results.ipynb",
    ]
    assert not (ROOT / "notebooks").exists()


def test_no_absolute_author_paths_in_source_configs_or_scripts():
    pattern = re.compile(r"[A-Za-z]:\\?Users\\?[A-Za-z0-9_.-]+|/c/Users/|/home/[a-z0-9_.-]+/")
    offenders = []
    for folder in ("src", "configs", "scripts", "notebook"):
        for f in (ROOT / folder).rglob("*"):
            if f.is_file() and f.suffix in {".py", ".json", ".yaml", ".sh", ".ipynb"} and "__pycache__" not in f.parts:
                if pattern.search(f.read_text(encoding="utf-8", errors="ignore")):
                    offenders.append(str(f.relative_to(ROOT)))
    assert offenders == []


def test_no_removed_modules_are_imported_by_active_code():
    old = re.compile(
        r"tcc_frota\.(v2|v3|algoritmos|availability|gold|ingestion|referencia|comparacao|sintetico|analise|leitura|extracao|privacidade)\b"
    )
    offenders = [
        str(f.relative_to(ROOT))
        for folder in ("src", "tests", "scripts")
        for f in (ROOT / folder).rglob("*.py")
        if old.search(f.read_text(encoding="utf-8", errors="ignore")) and f.name != "test_repository_structure.py"
    ]
    assert offenders == []


def test_no_empty_directories_in_active_tree():
    empty = []
    for folder in ("src", "configs", "tests", "scripts", "notebook", "docs"):
        for d in (ROOT / folder).rglob("*"):
            if d.is_dir() and "__pycache__" not in d.parts and not any(d.iterdir()):
                empty.append(str(d.relative_to(ROOT)))
    assert empty == []
