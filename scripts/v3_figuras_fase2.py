"""Figura vetorial da curva de poder e tabela de falsos positivos (Fase 2), a partir de reports/tcc_v2/fase2_curva_poder.csv."""

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tcc_v2"


def read(path):
    with open(path, encoding="utf-8", newline="") as h:
        return list(csv.DictReader(h))


def main() -> None:
    rows = read(OUT / "fase2_curva_poder.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.6), sharey=True)
    colors = {"mar2026": "#1f77b4", "set2026": "#d95f02"}
    styles = {"iid": "-", "circular_b3": "--"}
    for ax, (efeito, col, xcol, xlabel, sign) in zip(
        axes,
        (
            ("N", "rejeita_n_ic_mais_largo", "delta_n_pct_injetado", "Efeito injetado em corridas atendidas (ΔN, %)", 1),
            ("KM", "rejeita_km_ic_mais_largo", "reducao_km_pct_injetada", "Redução injetada no KM vazio por corrida (%)", -1),
        ),
    ):
        for periodo in colors:
            for mundo in styles:
                pts = sorted(
                    (
                        (sign * float(r[xcol]), float(r[col]))
                        for r in rows
                        if r["efeito"] == efeito
                        and r["periodo"] == periodo
                        and r["mundo_de_amostragem"] == mundo
                        and r["referencia_de_dispersao"] == "guloso_marginal_a0.1"
                    ),
                    key=lambda p: p[0],
                )
                if efeito == "KM":  # o ponto nulo (0) vem das linhas de efeito N
                    null = [
                        float(r[col])
                        for r in rows
                        if r["efeito"] == "N"
                        and float(r["delta_n_pct_injetado"]) == 0.0
                        and r["periodo"] == periodo
                        and r["mundo_de_amostragem"] == mundo
                        and r["referencia_de_dispersao"] == "guloso_marginal_a0.1"
                    ]
                    pts = [(0.0, null[0])] + pts
                ax.plot(
                    [p[0] for p in pts],
                    [p[1] for p in pts],
                    styles[mundo],
                    color=colors[periodo],
                    marker="o",
                    ms=3.5,
                    label=f"{'Mar' if periodo == 'mar2026' else 'Set'}/2026, amostragem {'iid' if mundo == 'iid' else 'em blocos de 3 dias'}",
                )
        ax.axhline(0.05, color="0.6", lw=0.8, ls=":")
        ax.axhline(0.80, color="0.6", lw=0.8, ls=":")
        ax.set_xlabel(xlabel)
        ax.set_ylim(-0.02, 1.02)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Fração de réplicas que rejeitam H0 (poder; no 0, falso positivo)")
    axes[1].legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "fase2_curva_poder.pdf")
    print("figura salva")


if __name__ == "__main__":
    sys.exit(main())
