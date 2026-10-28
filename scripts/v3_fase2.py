"""Fase 2 (semi-sintética) da v2: falsos positivos, poder e cobertura com efeito injetado conhecido. Não relê data/raw."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tcc_frota.v3 import fase2, inferencia as inf  # noqa: E402
from tcc_frota.v3.fase1 import write_csv  # noqa: E402

REFS = ("guloso_marginal_a0.1", "proporcional")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=Path, default=ROOT / "reports/runs/tcc_final/20261016T013428Z/individual/dias_cenarios.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "reports/tcc_v2")
    ap.add_argument("--replicas", type=int, default=1000)
    ap.add_argument("--reps", type=int, default=1000)
    a = ap.parse_args()
    pairs = inf.load_pairs(a.dias)
    rows = []
    for periodo in ("mar2026", "set2026"):
        for ref in REFS:
            for r in fase2.curve(pairs[(periodo, "04-11", "B", ref)], periodo, a.replicas, a.reps):
                rows.append({"referencia_de_dispersao": ref, **r})
    write_csv(a.out / "fase2_curva_poder.csv", rows)
    print(len(rows), "linhas")
