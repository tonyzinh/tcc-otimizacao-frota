"""Bloqueia, antes do commit, arquivos de dados, segredos e arquivos grandes (gancho do pre-commit).

Recebe os caminhos preparados para o commit (o pre-commit os passa como argumentos) e falha se algum:
- estiver em `data/` ou for de formato binário de dados (Parquet, pickle, Feather, SQLite...);
- parecer segredo (`.env`, chave, sal, `configs/private/`);
- passar de 5 MB (o PDF do artigo é a única exceção declarada).
Não lê o conteúdo dos arquivos.

    python scripts/check_data_files.py <arquivos...>
    python scripts/check_data_files.py --staged   # lê a lista do `git diff --cached`
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

MAX_BYTES = 5_000_000
ALLOWED_LARGE = {"article/ARTIGO_ATRIBUICAO_HUNGARO.pdf"}
DATA_EXT = {".parquet", ".parq", ".pq", ".pkl", ".pickle", ".feather", ".arrow", ".db", ".sqlite", ".sqlite3", ".xlsx", ".xls"}
SECRET = re.compile(r"(^|/)(\.env(\..+)?|.*\.(pem|p12|pfx|key|salt)|\.pseudo_salt|.*pseudo_secret.*|credentials.*\.json)$", re.I)


def problems(paths: list[str]) -> list[str]:
    out = []
    for raw in paths:
        p = raw.replace("\\", "/")
        if p.endswith(".env.example"):
            continue
        if p.startswith("data/"):
            out.append(f"{p}: arquivo em data/ (dados ficam locais)")
        elif Path(p).suffix.lower() in DATA_EXT:
            out.append(f"{p}: formato de dados ({Path(p).suffix})")
        if SECRET.search(p) or p.startswith("configs/private/"):
            out.append(f"{p}: possível segredo")
        f = Path(raw)
        if f.is_file() and f.stat().st_size > MAX_BYTES and p not in ALLOWED_LARGE:
            out.append(f"{p}: {f.stat().st_size:,} bytes (> {MAX_BYTES:,})")
    return out


def main(argv: list[str]) -> int:
    if argv[:1] == ["--staged"]:
        argv = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"], capture_output=True, text=True, check=True
        ).stdout.split()
    found = problems(argv)
    for f in found:
        print("BLOQUEADO:", f)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
