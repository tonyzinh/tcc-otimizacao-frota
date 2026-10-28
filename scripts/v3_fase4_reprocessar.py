"""Reprocessa a análise da Fase 4 a partir de reports/runs/tcc_v2/fase4_linhas_por_semente.csv (sem ressimular)."""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tcc_frota.v3 import fase4

if __name__ == "__main__":
    with open(ROOT / "reports/runs/tcc_v2/fase4_linhas_por_semente.csv", encoding="utf-8", newline="") as h:
        rows = list(csv.DictReader(h))
    print(json.dumps(fase4.finish(rows, ROOT / "reports/tcc_v2", 10000), indent=2, ensure_ascii=False))
