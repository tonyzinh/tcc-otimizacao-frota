"""Funções reutilizáveis de figuras (PDF vetorial e PNG), com paleta única e eixos que partem do zero nas barras.

Todas recebem DataFrames ou dicionários já calculados por ``tcc_frota.metrics`` e gravam em uma pasta de saída. Nenhuma lê dados brutos.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PALETTE = {"A": "#7f7f7f", "B": "#c97a2b", "C": "#1f4e79", "CxB": "#7aa6c9"}
CONTRAST_COLORS = {"C × A": "#1f4e79", "C × B": "#7aa6c9", "B × A": "#c97a2b"}
PERIOD_LABELS = {"replicacao": "Setembro (15 dias)", "final": "Outubro (25 dias)"}
CHANGE_KEY = "variacao_km_vazio_pct (negativo = reducao)"
# Preenchimento legível em impressão em tons de cinza: tom e hachura distintos por contraste (a cor não é o único código).
CONTRAST_STYLE = {
    "C × A": {"color": "0.25", "hatch": "", "label": "atribuição conjunta − despacho imediato"},
    "C × B": {"color": "0.65", "hatch": "///", "label": "atribuição conjunta − lote sequencial"},
    "B × A": {"color": "1.0", "hatch": "...", "label": "lote sequencial − despacho imediato"},
}


def _style() -> None:
    plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"], "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def _save(fig, out: Path, name: str) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ("pdf", "png"):
        p = out / f"{name}.{ext}"
        fig.savefig(p, dpi=200 if ext == "png" else None, bbox_inches="tight")
        paths.append(p)
    plt.close(fig)
    return paths


def _comma(v: float, fmt: str) -> str:
    return format(v, fmt).replace(".", ",")


def plot_km_and_attendance(summary: dict, out: Path, name: str = "empty_km_service_differences") -> list[Path]:
    """Duas faixas: variação do km vazio (%) e do atendimento (p.p.) por contraste e período. Negativo no km = redução.

    Cada contraste tem tom de cinza e hachura próprios, para que a figura continue legível impressa sem cor.
    """
    _style()
    fig, ax = plt.subplots(1, 2, figsize=(6.3, 3.1))
    width, x = 0.25, np.arange(len(PERIOD_LABELS))
    for i, contrast in enumerate(CONTRAST_COLORS):
        km, att = [], []
        for period in PERIOD_LABELS:
            row = next(c for c in summary[period]["contrastes"] if c["contraste"] == contrast)
            km.append(row[CHANGE_KEY])
            att.append(row["diferenca_atendimento_pontos_percentuais"])
        st = CONTRAST_STYLE[contrast]
        kw = {"color": st["color"], "hatch": st["hatch"], "edgecolor": "k", "linewidth": 0.6, "label": st["label"]}
        b1 = ax[0].bar(x + (i - 1) * width, km, width, **kw)
        b2 = ax[1].bar(x + (i - 1) * width, att, width, **kw)
        for r, v in zip(b1, km, strict=True):
            ax[0].text(r.get_x() + r.get_width() / 2, v - 0.25, _comma(v, ".1f"), ha="center", va="top", fontsize=7.5)
        for r, v in zip(b2, att, strict=True):
            ax[1].text(
                r.get_x() + r.get_width() / 2,
                v + (0.05 if v >= 0 else -0.05),
                _comma(v, "+.2f"),
                ha="center",
                va="bottom" if v >= 0 else "top",
                fontsize=7.5,
            )
    for a, title, ylabel in (
        (ax[0], "(a) Variação do km vazio", "variação do km vazio (%)\nnegativo = menos km"),
        (ax[1], "(b) Variação do atendimento", "variação do atendimento (p.p.)\nnegativo = menos atendidos"),
    ):
        a.axhline(0, color="k", lw=0.8)
        a.set_xticks(x)
        a.set_xticklabels(PERIOD_LABELS.values())
        a.set_title(title, fontsize=9, loc="left")
        a.set_ylabel(ylabel, fontsize=8)
    ax[0].set_ylim(-7.3, 0.5)
    ax[1].set_ylim(-1.5, 1.6)
    handles, labels = ax[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=8, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    return _save(fig, out, name)


def plot_daily_differences(daily_km: pd.DataFrame, out: Path, period: str, name: str | None = None) -> list[Path]:
    """Diferença diária de km vazio C − A (barras por dia). `daily_km`: índice = dia, colunas = nomes gravados das políticas."""
    _style()
    diff = daily_km["B_lote60s_hungaro"] - daily_km["B0_imediato_atual"]
    fig, ax = plt.subplots(figsize=(6.3, 2.6))
    ax.bar(range(len(diff)), diff.to_numpy(), color=np.where(diff <= 0, PALETTE["C"], "#b03a2e"))
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(range(len(diff)))
    ax.set_xticklabels([str(d)[-5:] for d in diff.index], rotation=70, ha="right", fontsize=7)
    ax.set_ylabel("C − A (km vazio por dia)\nnegativo = redução", fontsize=8)
    ax.set_title(f"Diferença diária pareada, {PERIOD_LABELS.get(period, period)} (vermelho = dia em que C piora)", fontsize=9, loc="left")
    fig.tight_layout()
    return _save(fig, out, name or f"daily_differences_{period}")


def plot_confidence_intervals(summary: dict, out: Path, name: str = "daily_difference_intervals") -> list[Path]:
    """IC95% (bootstrap de blocos) da diferença média diária de km vazio, por contraste e período."""
    _style()
    fig, ax = plt.subplots(figsize=(6.3, 2.6))
    y = 0
    labels = []
    for period, plabel in PERIOD_LABELS.items():
        for contrast, color in CONTRAST_COLORS.items():
            row = next(c for c in summary[period]["contrastes"] if c["contraste"] == contrast)
            lo, hi = row["ic95_diferenca_media_diaria_km"]
            mid = row["diferenca_media_diaria_km"]
            ax.errorbar(mid, y, xerr=[[mid - lo], [hi - mid]], fmt="o", color=color, capsize=3)
            labels.append(f"{contrast} · {plabel.split(' ')[0]}")
            y += 1
    ax.axvline(0, color="k", lw=0.8)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Diferença média diária de km vazio (IC95%, bootstrap de blocos de 7 dias)", fontsize=8)
    fig.tight_layout()
    return _save(fig, out, name)


def plot_attendance_vs_km(summary: dict, out: Path, name: str = "service_vs_empty_km") -> list[Path]:
    """Dispersão: variação do km vazio (%) × variação do atendimento (p.p.), um ponto por contraste e período."""
    _style()
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    for period, marker in zip(PERIOD_LABELS, ("o", "s"), strict=True):
        for contrast, color in CONTRAST_COLORS.items():
            row = next(c for c in summary[period]["contrastes"] if c["contraste"] == contrast)
            ax.scatter(
                row["diferenca_atendimento_pontos_percentuais"],
                row[CHANGE_KEY],
                color=color,
                marker=marker,
                s=40,
                label=f"{contrast} · {PERIOD_LABELS[period].split(' ')[0]}",
            )
    ax.axhline(0, color="k", lw=0.6)
    ax.axvline(0, color="k", lw=0.6)
    ax.set_xlabel("Variação do atendimento (p.p.)", fontsize=8)
    ax.set_ylabel("Variação do km vazio (%)", fontsize=8)
    ax.legend(frameon=False, fontsize=7, loc="lower left")
    fig.tight_layout()
    return _save(fig, out, name)


def plot_wait_by_policy(summary: dict, out: Path, name: str = "wait_by_policy") -> list[Path]:
    """Espera média e P90 por política e período. A espera é medida SÓ entre os pedidos atendidos (denominadores no rótulo)."""
    _style()
    fig, ax = plt.subplots(1, 2, figsize=(6.3, 2.8), sharey=True)
    for a, (period, plabel) in zip(ax, PERIOD_LABELS.items(), strict=True):
        rows = summary[period]["absolutos"]
        names = [r["politica"].split(" ·")[0] for r in rows]
        mean = [r["espera_media_s"] for r in rows]
        p90 = [r["espera_p90_s"] for r in rows]
        x = np.arange(len(rows))
        a.bar(x - 0.2, mean, 0.4, color="#7aa6c9", label="média")
        a.bar(x + 0.2, p90, 0.4, color="#1f4e79", label="P90")
        a.set_xticks(x)
        a.set_xticklabels([f"{n}\n(n={r['atendidos']:,})".replace(",", ".") for n, r in zip(names, rows, strict=True)], fontsize=8)
        a.set_title(plabel, fontsize=9, loc="left")
    ax[0].set_ylabel("Espera dos atendidos (s)", fontsize=8)
    ax[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    return _save(fig, out, name)


def plot_synthetic_summary(table: pd.DataFrame, out: Path, name: str = "synthetic_contrasts") -> list[Path]:
    """Variação do km vazio (%) de B e C contra A nos cenários sintéticos. Os cenários compartilham estrutura: não são 22 confirmações."""
    _style()
    c = table[(table.politica == "D_lote60s_hungaro") & (table.referencia == "A")].reset_index(drop=True)
    b = table[(table.politica == "D_lote60s_guloso_fifo") & (table.referencia == "A")].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(6.3, 3.0))
    idx = np.arange(len(c))
    ax.bar(idx - 0.2, c.d_pct, 0.4, color=PALETTE["C"], label="C: húngaro, lote de 60 s")
    ax.bar(idx + 0.2, b.d_pct, 0.4, color=PALETTE["B"], label="B: mais próximo, lote de 60 s")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(idx)
    ax.set_xticklabels(c.cenario.str.replace("_", " "), rotation=70, ha="right", fontsize=7)
    ax.set_ylabel("Variação do km vazio vs. A (%)", fontsize=8)
    ax.set_ylim(min(-16, float(min(c.d_pct.min(), b.d_pct.min())) - 1), 3)
    ax.legend(frameon=False, fontsize=8, loc="upper center", ncol=2)
    fig.tight_layout()
    return _save(fig, out, name)


def make_all(historical_dir: Path, synthetic_dir: Path, out: Path) -> list[Path]:
    """Gera todas as figuras que dependem apenas de tabelas já calculadas (resumo.json, *_km_vazio_por_dia.csv, resumo_contrastes.csv)."""
    paths: list[Path] = []
    summary = json.loads((historical_dir / "resumo.json").read_text(encoding="utf-8"))
    paths += plot_km_and_attendance(summary, out)
    paths += plot_confidence_intervals(summary, out)
    paths += plot_attendance_vs_km(summary, out)
    paths += plot_wait_by_policy(summary, out)
    for period in PERIOD_LABELS:
        csv = historical_dir / f"{period}_km_vazio_por_dia.csv"
        if csv.exists():
            paths += plot_daily_differences(pd.read_csv(csv, index_col=0), out, period)
    synth_csv = synthetic_dir / "resumo_contrastes.csv"
    if synth_csv.exists():
        paths += plot_synthetic_summary(pd.read_csv(synth_csv), out)
    return paths
