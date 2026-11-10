"""Compila o artigo (XeLaTeX → BibTeX → XeLaTeX ×2) e copia o PDF para o nome final de entrega.

O nome final é fixo (pedido dos autores): ``article/TCC 2026-2 - Entony Jovino - Raphael Simões - Orientador Rober Marcone Rosi.pdf``.
A cópia só é feita se a compilação terminar sem erro de LaTeX e sem referência ou citação indefinida.

    python scripts/build_article.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLE = ROOT / "article"
FINAL_PDF_NAME = "TCC 2026-2 - Entony Jovino - Raphael Simões - Orientador Rober Marcone Rosi.pdf"
FINAL_PDF = ARTICLE / FINAL_PDF_NAME


def _run(cmd: list[str]) -> str | None:
    result = subprocess.run(cmd, cwd=ARTICLE, capture_output=True, text=True, errors="replace", check=False)
    if result.returncode == 0:
        return None
    details = (result.stderr or result.stdout).strip().splitlines()
    return f"{' '.join(cmd)} falhou (código {result.returncode}): {details[-1] if details else 'sem diagnóstico'}"


def build() -> list[str]:
    """Compila e devolve a lista de problemas encontrados no log (vazia quando a compilação está limpa)."""
    xelatex = ["xelatex", "-interaction=nonstopmode", "-output-directory=build", "main.tex"]
    for cmd in (xelatex, ["bibtex", "build/main"], xelatex, xelatex):
        failure = _run(cmd)
        if failure:
            return [failure]
    log = (ARTICLE / "build" / "main.log").read_text(encoding="utf-8", errors="replace")
    problems = [line for line in log.splitlines() if line.startswith("! ")]
    problems += re.findall(r"LaTeX Warning: (?:Reference|Citation) .* undefined.*", log)
    if not (ARTICLE / "build" / "main.pdf").exists():
        problems.append("build/main.pdf não foi gerado")
    return problems


def main() -> int:
    problems = build()
    for p in problems:
        print("PROBLEMA:", p)
    if problems:
        print("PDF final não atualizado.")
        return 1
    shutil.copyfile(ARTICLE / "build" / "main.pdf", FINAL_PDF)
    overfull = (ARTICLE / "build" / "main.log").read_text(encoding="utf-8", errors="replace").count("Overfull")
    print(f"copiado: article/{FINAL_PDF_NAME} | overfull: {overfull}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
