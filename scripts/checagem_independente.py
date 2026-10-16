"""Checagem independente do resultado principal da bateria (não importa o pacote `tcc_frota`).

Lê `resultados/finalistas_<mes>_dias.csv`, agrega as sementes por dia, recalcula a variação do KM vazio
total por corrida e das corridas (regime B) com bootstrap pareado de dias em NumPy (gerador diferente
do usado na bateria) e confere B + R = total linha a linha. Uso: python scripts/checagem_independente.py [pasta]
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPS = 4000


def load(path: Path):
    acc = defaultdict(lambda: defaultdict(list))
    bad = 0
    for r in csv.DictReader(path.open(encoding="utf-8")):
        if r["regime"] != "B":
            continue
        p, rep, e = float(r["pickup_km"]), float(r["reposition_km"]), float(r["empty_km"])
        bad += abs(p + rep - e) > 1e-4
        acc[r["cenario"]][r["data"]].append((float(r["served"]), e))
    days = {c: {d: np.mean(v, axis=0) for d, v in dd.items()} for c, dd in acc.items()}
    return days, bad


def main() -> int:
    rng = np.random.default_rng(987654321)
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("resultados")   # ex.: resultados/seletivo
    for month in ("marco", "setembro"):
        path = folder / f"finalistas_{month}_dias.csv"
        if not path.exists():
            continue
        days, bad = load(path)
        base = days["sem_reposicionamento"]
        dates = sorted(base)
        b = np.array([base[d] for d in dates])
        print(f"\n{month}: {len(dates)} dias; linhas com B+R != total: {bad}")
        for c in sorted(k for k in days if k != "sem_reposicionamento"):
            p = np.array([days[c][d] for d in dates])
            idx = rng.integers(0, len(dates), size=(REPS, len(dates)))
            ratio = lambda pp, bb: (pp[..., 1].sum(-1) / pp[..., 0].sum(-1)) / (bb[..., 1].sum(-1) / bb[..., 0].sum(-1)) - 1
            served = lambda pp, bb: pp[..., 0].sum(-1) / bb[..., 0].sum(-1) - 1
            km_point, km_boot = ratio(p, b), ratio(p[idx], b[idx])
            sv_point, sv_boot = served(p, b), served(p[idx], b[idx])
            lo, hi = np.percentile(km_boot, [2.5, 97.5])
            slo, shi = np.percentile(sv_boot, [2.5, 97.5])
            print(f"  {c:<28} km vazio/corrida {100 * km_point:+7.2f}% [{100 * lo:+.2f}; {100 * hi:+.2f}]   "
                  f"corridas {100 * sv_point:+6.2f}% [{100 * slo:+.2f}; {100 * shi:+.2f}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
