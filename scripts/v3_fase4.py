"""Fase 4 da v2 (baselines B0-B4, rho, conformidade). Exige TCC_REAL_DATA_AUTHORIZED=YES (local, só agregados)."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if __name__ == "__main__":
    if os.environ.get("TCC_REAL_DATA_AUTHORIZED") != "YES":
        sys.exit("defina TCC_REAL_DATA_AUTHORIZED=YES (processamento local autorizado)")
    from tcc_frota.v3 import fase4
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=ROOT / "data/raw")
    ap.add_argument("--out", type=Path, default=ROOT / "reports/tcc_v2")
    ap.add_argument("--runs", type=Path, default=ROOT / "reports/runs/tcc_v2")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--reps", type=int, default=10000)
    a = ap.parse_args()
    print(json.dumps(fase4.run(a.raw, a.out, a.runs, a.workers, a.reps), indent=2, ensure_ascii=False))
