"""Fase 1 da v2: executa `tcc_frota.v3.fase1.run` sobre as tabelas diárias derivadas (sem reler data/raw)."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tcc_frota.v3 import fase1

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=Path, default=ROOT / "reports/runs/tcc_final/20261016T013428Z/individual/dias_cenarios.csv")
    ap.add_argument("--tab11", type=Path, default=ROOT / "reports/tcc_final/tab11_principal.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "reports/tcc_v2")
    ap.add_argument("--reps", type=int, default=10000)
    a = ap.parse_args()
    print(json.dumps(fase1.run(a.dias, a.tab11, a.out, a.reps), indent=2, ensure_ascii=False))
