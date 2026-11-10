"""Figura da rodada 5 (pós-hoc): diferenças diárias C×A e C×B ao longo de 2026, a partir dos CSV agregados por dia.

Lê só `reports/diagnostics/calibration/recalibration_out_of_sample/{mensal,setout,teste}_por_dia.csv` (totais por dia e política; nada individual) e grava
`reports/figures/recalibration_daily_differences.pdf` (origem oficial; a cópia do artigo vem de `scripts/sync_article_figures.py`). Não roda simulação nem lê dados brutos.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

R5 = Path("reports/diagnostics/calibration/recalibration_out_of_sample")
OUT = Path("reports/figures/recalibration_daily_differences.pdf")


def _diarios() -> pd.DataFrame:
    fontes = {
        "fev–ago (calibração até o mês anterior)": R5 / "mensal_por_dia.csv",
        "set–out (calibração nova)": R5 / "setout_por_dia.csv",
        "26/10–08/11 (teste fora da amostra)": R5 / "teste_por_dia.csv",
    }
    rows = []
    for rotulo, p in fontes.items():
        df = pd.read_csv(p)
        if "variante" in df:
            df = df[df.variante.isin(["calibracao_nova"]) | df.variante.str.startswith("mes_")]
        w = df.pivot_table(index="dia", columns="politica", values=["km_vazio", "atendidos"], aggfunc="sum")
        rows.append(
            pd.DataFrame(
                {
                    "dia": pd.to_datetime(w.index),
                    "serie": rotulo,
                    "CxA_km_pct": 100 * (w.km_vazio.C - w.km_vazio.A) / w.km_vazio.A,
                    "CxB_km_pct": 100 * (w.km_vazio.C - w.km_vazio.B) / w.km_vazio.B,
                    "CxA_dN": w.atendidos.C - w.atendidos.A,
                }
            )
        )
    return pd.concat(rows, ignore_index=True).sort_values("dia")


def main() -> None:
    d = _diarios()
    plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"], "font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(2, 1, figsize=(6.3, 4.8), sharex=True)
    # Marcadores de forma diferente (cheio e vazado) e barras cheias/vazadas: legível impresso em tons de cinza.
    estilos = {
        "CxA_km_pct": {"marker": "o", "mfc": "0.15", "mec": "0.15", "label": "atribuição conjunta − despacho imediato"},
        "CxB_km_pct": {"marker": "^", "mfc": "white", "mec": "0.35", "label": "atribuição conjunta − lote sequencial"},
    }
    for col, st in estilos.items():
        ax[0].plot(d.dia, d[col], linestyle="none", ms=3, mew=0.6, **st)
    ax[0].axhline(0, color="0.4", lw=0.6)
    ax[0].set_title("(a) Variação do km vazio no dia", fontsize=8, loc="left")
    ax[0].set_ylabel("variação do km vazio (%)\nnegativo = menos km")
    ax[0].set_ylim(bottom=-21)  # espaço para a legenda sem cobrir pontos
    ax[0].legend(frameon=False, loc="lower left", ncol=2)
    pos = d.CxA_dN >= 0
    ax[1].bar(d.dia[pos], d.CxA_dN[pos], width=0.9, color="0.3", edgecolor="0.3", lw=0.3, label="conjunta atende mais ou igual")
    ax[1].bar(d.dia[~pos], d.CxA_dN[~pos], width=0.9, color="white", edgecolor="0.1", lw=0.5, label="conjunta atende menos")
    ax[1].axhline(0, color="0.4", lw=0.6)
    ax[1].set_title("(b) Diferença de atendidos no dia: atribuição conjunta − despacho imediato", fontsize=8, loc="left")
    ax[1].set_ylabel("diferença de atendidos\n(pedidos por dia)")
    ax[1].set_xlabel("mês/ano (2026)")
    ax[1].set_ylim(bottom=-62)
    ax[1].legend(frameon=False, loc="lower left", ncol=2)
    for a in ax:
        a.axvspan(pd.Timestamp("2026-10-26"), pd.Timestamp("2026-11-08"), color="0.9", zorder=0)
        a.axvspan(pd.Timestamp("2026-09-01"), pd.Timestamp("2026-09-15"), color="white", zorder=0)
    ax[1].xaxis.set_major_locator(mdates.MonthLocator())
    ax[1].xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
    ax[0].text(pd.Timestamp("2026-10-27"), ax[0].get_ylim()[1] * 0.9, "teste", fontsize=7, va="top")
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT)
    print(OUT, len(d), "dias")


if __name__ == "__main__":
    main()
