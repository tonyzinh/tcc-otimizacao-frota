"""Copia para `article/figures/` as figuras que o artigo inclui, a partir da origem oficial `reports/figures/`, ou confere a cópia.

A lista de figuras vem do próprio LaTeX (`\\includegraphics{figures/...}` e `\\figura[...]{figures/...}`), então uma figura nova no texto
entra sem editar este script. Com `--check`, nada é gravado: o script falha se faltar a origem ou a cópia, se o SHA-256 diferir, ou se
houver em `article/figures/` arquivo que o artigo não usa.

    python scripts/sync_article_figures.py            # copia
    python scripts/sync_article_figures.py --check    # só confere (usado nos testes)
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLE = ROOT / "article"
SOURCE = ROOT / "reports" / "figures"
TARGET = ARTICLE / "figures"
PATTERN = re.compile(r"(?:\\includegraphics|\\figura)(?:\[[^\]]*\])?\{figures/([^}]+)\}")


def referenced() -> list[str]:
    """Nomes de arquivo em `figures/` citados nos .tex do artigo, sem repetição e em ordem."""
    names: list[str] = []
    for tex in sorted(ARTICLE.rglob("*.tex")):
        if "build" in tex.relative_to(ARTICLE).parts:
            continue
        for name in PATTERN.findall(tex.read_text(encoding="utf-8")):
            if name not in names:
                names.append(name)
    return names


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check() -> list[str]:
    """Lista de problemas; vazia quando as cópias do artigo conferem com a origem."""
    problems = []
    names = referenced()
    for name in names:
        src, dst = SOURCE / name, TARGET / name
        if not src.exists():
            problems.append(f"origem ausente: reports/figures/{name}")
        elif not dst.exists():
            problems.append(f"cópia ausente: article/figures/{name}")
        elif sha256(src) != sha256(dst):
            problems.append(f"cópia diferente da origem: {name}")
    extras = sorted(p.name for p in TARGET.glob("*") if p.is_file() and p.name not in names) if TARGET.exists() else []
    problems += [f"arquivo não usado pelo artigo: article/figures/{e}" for e in extras]
    return problems


def sync() -> list[str]:
    TARGET.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in referenced():
        src = SOURCE / name
        if not src.exists():
            raise FileNotFoundError(f"origem ausente: {src.relative_to(ROOT)}")
        shutil.copyfile(src, TARGET / name)
        copied.append(name)
    return copied


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="só confere; não copia")
    a = ap.parse_args()
    if not a.check:
        for name in sync():
            print("copiado:", name)
    problems = check()
    for p in problems:
        print("PROBLEMA:", p)
    print("figuras do artigo:", len(referenced()), "| problemas:", len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
