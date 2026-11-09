"""Manifesto de checksums dos dados locais (`data/`): caminho relativo, bytes e SHA-256, sem conteúdo.

O manifesto é versionado (`reports/manifests/data_checksums.csv`); os dados não. Serve para conferir se uma cópia local dos dados
é a mesma usada nos resultados, sem publicar os dados.

    python scripts/data_checksums.py            # (re)gera o manifesto
    python scripts/data_checksums.py --check    # confere data/ contra o manifesto; sai com 1 se algo faltar ou diferir
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MANIFEST = ROOT / "reports" / "manifests" / "data_checksums.csv"
FIELDS = ["caminho", "bytes", "sha256"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def scan(data: Path = DATA) -> list[dict[str, str]]:
    rows = []
    for p in sorted(data.rglob("*")):
        if p.is_file():
            rows.append({"caminho": p.relative_to(ROOT).as_posix(), "bytes": str(p.stat().st_size), "sha256": sha256(p)})
    return rows


def write(rows: list[dict[str, str]], out: Path = MANIFEST) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def compare(rows: list[dict[str, str]], manifest: Path = MANIFEST) -> dict[str, list[str]]:
    with manifest.open(encoding="utf-8") as fh:
        ref = {r["caminho"]: r for r in csv.DictReader(fh)}
    cur = {r["caminho"]: r for r in rows}
    return {
        "ausentes": sorted(set(ref) - set(cur)),
        "novos": sorted(set(cur) - set(ref)),
        "diferentes": sorted(k for k in set(ref) & set(cur) if ref[k]["sha256"] != cur[k]["sha256"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if not DATA.exists():
        print("data/ não existe nesta cópia; ver docs/reproducibility.md (obtenção dos dados)")
        return 1
    rows = scan()
    if not a.check:
        write(rows)
        print(f"{MANIFEST.relative_to(ROOT)}: {len(rows)} arquivos, {sum(int(r['bytes']) for r in rows):,} bytes")
        return 0
    diff = compare(rows)
    for k, v in diff.items():
        print(f"{k}: {len(v)}", *v[:10], sep="\n  ")
    return 1 if diff["ausentes"] or diff["diferentes"] else 0


if __name__ == "__main__":
    sys.exit(main())
