"""Confere os resultados congelados pelo conteúdo (SHA-256), seguindo o mapa de caminhos antigo -> novo da reestruturação.

1. Estudo anterior (``reports/tcc_final``, hoje fora da árvore ativa): 19 hashes do pré-registro (``docs/V2_PREREGISTRO.md`` no commit
   ``cb00ee3``).
2. Arquivos rastreados no commit de referência (``--ref``, padrão ``3e65f3b``) dentro dos diretórios congelados: SHA-256 do conteúdo atual,
   no caminho novo, contra o blob do commit (CRLF normalizado para LF, como o Git armazena).
3. Parquets não rastreados da avaliação congelada: SHA-256 atual contra o registrado na conferência anterior (``--previous``).

Só lê arquivos. Uso: ``python scripts/verify_frozen_results.py [--archive PASTA] [--out CSV]``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH_MAP = ROOT / "reports/manifests/repository_restructure/path_map.csv"
DEFAULT_ARCHIVE = ROOT.parent / "tcc-otimizacao-frota_preservacao_2026-11-09" / "estudo_anterior_retirado_da_arvore"
DEFAULT_PREVIOUS = ROOT / "reports/diagnostics/consistency/article_anonymization_check/hashes_congelados.csv"
FROZEN_OLD = ["reports/atribuicao_final", "reports/sintetico_v2", "reports/tcc_final", "resultados"]
ARCHIVE_PREFIX = "@preservacao/estudo_anterior_retirado_da_arvore"


def git(*args: str) -> bytes:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, check=True).stdout


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_map() -> list[tuple[str, str]]:
    with PATH_MAP.open(encoding="utf-8") as fh:
        return [(r["caminho_antigo"], r["caminho_novo"]) for r in csv.DictReader(fh)]


def resolve(old: str, mapping: list[tuple[str, str]], archive: Path) -> Path:
    """Caminho atual de um arquivo pelo caminho antigo (prefixo mais longo do mapa)."""
    best = max((m for m in mapping if old == m[0] or old.startswith(m[0] + "/")), key=lambda m: len(m[0]), default=None)
    new = old if best is None else best[1] + old[len(best[0]) :]
    if new.startswith(ARCHIVE_PREFIX):
        return archive / new[len(ARCHIVE_PREFIX) + 1 :]
    return ROOT / new


def shown(p: Path, archive: Path) -> str:
    """Caminho para o relatório, sem caminho absoluto da máquina: relativo ao repositório ou com o prefixo da preservação."""
    if p.is_relative_to(ROOT):
        return p.relative_to(ROOT).as_posix()
    if p.is_relative_to(archive):
        return f"{ARCHIVE_PREFIX}/{p.relative_to(archive).as_posix()}"
    return p.name


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    ap.add_argument("--previous", type=Path, default=DEFAULT_PREVIOUS)
    ap.add_argument("--ref", default="3e65f3b")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    mapping = load_map()
    rows: list[list] = []

    prereg = git("show", "cb00ee3:docs/V2_PREREGISTRO.md").decode("utf-8")
    table = dict(re.findall(r"\|\s*([\w.]+\.(?:csv|json))\s*\|\s*([0-9a-f]{64})\s*\|", prereg))
    tcc_final = resolve("reports/tcc_final", mapping, a.archive)
    for name, h in sorted(table.items()):
        found = list(tcc_final.rglob(name))
        cur = sha(found[0].read_bytes()) if found else "AUSENTE"
        rows.append(
            ["tcc_final_preregistro", f"reports/tcc_final/.../{name}", shown(found[0], a.archive) if found else "", h, cur, cur == h]
        )

    for d in FROZEN_OLD:
        for old in git("ls-tree", "-r", "--name-only", a.ref, d).decode().splitlines():
            blob = git("cat-file", "blob", f"{a.ref}:{old}")
            p = resolve(old, mapping, a.archive)
            cur_b = p.read_bytes() if p.exists() else b""
            ok = p.exists() and sha(cur_b.replace(b"\r\n", b"\n")) == sha(blob.replace(b"\r\n", b"\n"))
            rows.append([f"git_{a.ref}", old, shown(p, a.archive), sha(blob), sha(cur_b), ok])

    if a.previous.exists():
        with a.previous.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["referencia"] != "sem_hash_registrado":
                    continue
                p = resolve(r["arquivo"], mapping, a.archive)
                cur = sha(p.read_bytes()) if p.exists() else "AUSENTE"
                rows.append(
                    [
                        "parquet_conferencia_anterior",
                        r["arquivo"],
                        shown(p, a.archive),
                        r["sha256_atual"],
                        cur,
                        cur == r["sha256_atual"],
                    ]
                )

    fails = sum(1 for r in rows if r[-1] is not True)
    for ref in sorted({r[0] for r in rows}):
        sel = [r for r in rows if r[0] == ref]
        print(f"{ref}: {sum(r[-1] is True for r in sel)}/{len(sel)} iguais")
    print("falhas:", fails)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["referencia", "caminho_antigo", "caminho_atual", "sha256_registrado", "sha256_atual", "igual"])
            w.writerows(rows)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
