"""Mapa de calor ρ × conformidade e tabelas .tex da v2, a partir dos CSV de reports/tcc_v2/.

Padrão de `tcc-artigo-latex/scripts/gerar_tabelas.py` (formatação pt-BR, macros em numeros_v2.tex), mas escreve em
reports/tcc_v2/tex/ e não edita os .tex do artigo. Sem leitura de dados individuais.
"""

import csv
import math
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tcc_v2"
TEX = OUT / "tex"
BASELINES = ("B0", "B1", "B2", "B3", "B4")
RHOS, CONFS = (0.25, 0.5, 0.75, 1.0), (0.5, 0.75, 1.0)


def read(name):
    with open(OUT / name, encoding="utf-8", newline="") as h:
        return list(csv.DictReader(h))


def fl(x):
    return float("nan") if x in ("", None) else float(x)


def num(x, casas=1, sinal=False):
    if x is None or math.isnan(x):
        return "---"
    s = f"{abs(x):,.{casas}f}".replace(",", "X").replace(".", "{,}").replace("X", ".")
    pre = "-" if x < 0 and round(abs(x), casas) != 0 else ("+" if sinal else "")
    return f"${pre}{s}$"


def heatmap() -> None:
    rows = read("fase4_grade_rho_conformidade.csv")
    nb = read("fase4_grade_rho_conformidade_nb.csv")
    fig, axes = plt.subplots(2, 5, figsize=(13, 5.2), sharex=True, sharey=True)
    for i, periodo in enumerate(("mar2026", "set2026")):
        for j, bk in enumerate(BASELINES):
            med = np.full((len(CONFS), len(RHOS)), np.nan)
            frac = np.zeros((len(CONFS), len(RHOS)))
            for a, c in enumerate(CONFS):
                for b, r in enumerate(RHOS):
                    sel = [
                        x
                        for x in rows
                        if x["periodo"] == periodo
                        and float(x["rho"]) == r
                        and float(x["conformidade"]) == c
                        and x["grupo"].split("|")[1] == bk
                    ]
                    med[a, b] = statistics.median(fl(x["km_vazio_pct"]) for x in sel)
                    cells = [
                        x
                        for x in nb
                        if x["periodo"] == periodo
                        and float(x["rho"]) == r
                        and float(x["conformidade"]) == c
                        and x["grupo"].split("|")[1] == bk
                        and float(x["e_star"]) == 30.0
                    ]
                    frac[a, b] = np.mean([fl(x["ic_inf"]) > 0 for x in cells])
            ax = axes[i, j]
            lim = max(1.0, np.nanmax(np.abs(med)))
            ax.imshow(med, cmap="RdBu_r", vmin=-lim, vmax=lim, origin="lower", aspect="auto")
            for a in range(len(CONFS)):
                for b in range(len(RHOS)):
                    ax.text(b, a, f"{med[a, b]:+.1f}\n({frac[a, b]:.0%})", ha="center", va="center", fontsize=6)
            ax.set_xticks(range(len(RHOS)), [f"{r:g}" for r in RHOS])
            ax.set_yticks(range(len(CONFS)), [f"{c:g}" for c in CONFS])
            ax.set_title(f"{'Mar' if periodo == 'mar2026' else 'Set'} · {bk}", fontsize=8)
    for ax in axes[1]:
        ax.set_xlabel("ρ (recuperabilidade)")
    for ax in axes[:, 0]:
        ax.set_ylabel("conformidade")
    fig.suptitle(
        "Mediana entre os 10 algoritmos de ΔKM vazio/corrida (%); entre parênteses, fração com NB(e*=30) > 0 e IC inteiro acima de zero",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(OUT / "fase4_mapa_calor_rho_conformidade.pdf")


def tabela_baselines() -> None:
    TEX.mkdir(exist_ok=True)
    lines = [
        r"% Gerado por scripts/v3_gerar_saidas.py; não edite à mão.",
        r"\begin{tabular}{llrrrr}",
        r"\hline",
        r"Período & Baseline & $\Delta$KM vazio/corrida (\%) mediana & mín.--máx. & $\Delta$N (\%) mediana & plano $-$ placebo (\%) \\",
        r"\hline",
    ]
    rows = read("fase4_F4_origem_linhas.csv")
    plc = read("fase4_plano_vs_placebo_origem_linhas.csv")
    for periodo in ("mar2026", "set2026"):
        for bk in BASELINES:
            sel = [x for x in rows if x["periodo"] == periodo and x["grupo"].split("|")[1] == bk]
            km = [fl(x["km_vazio_pct"]) for x in sel]
            n = [fl(x["atendidas_pct"]) for x in sel]
            pp = [fl(x["km_vazio_pct"]) for x in plc if x["periodo"] == periodo and x["grupo"].split("|")[1] == bk]
            lines.append(
                f"{'Mar' if periodo == 'mar2026' else 'Set'}/2026 & {bk} & {num(statistics.median(km), 1, True)} & "
                f"{num(min(km), 1, True)}--{num(max(km), 1, True)} & {num(statistics.median(n), 2, True)} & "
                f"{num(statistics.median(pp), 1, True) if pp else '---'} \\\\"
            )
    lines += [r"\hline", r"\end{tabular}"]
    (TEX / "fase4_baselines.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def tabela_inferencia() -> None:
    rows = read("fase1_comparacao_v1_v2.csv")
    prim = [r for r in rows if r["janela"] == "04-11" and r["regime"] == "B"]
    lines = [
        r"% Gerado por scripts/v3_gerar_saidas.py; não edite à mão.",
        r"\begin{tabular}{llrrrr}",
        r"\hline",
        r"Período & Cenário & $\Delta$KM/corrida (\%) & IC v1 & IC v2 (mais largo) & $p$-RW \\",
        r"\hline",
    ]
    for r in prim:
        lines.append(
            f"{r['periodo'][:3].capitalize()} & {r['cenario'].replace('_', ' ')} & {num(fl(r['v1_km_vazio_pct']), 1, True)} & "
            f"[{num(fl(r['v1_ic_percentil_inf']), 1)}; {num(fl(r['v1_ic_percentil_sup']), 1)}] & "
            f"[{num(fl(r['v2_ic_decisao_inf']), 1)}; {num(fl(r['v2_ic_decisao_sup']), 1)}] & {num(fl(r['v2_p_rw_F1']), 3)} \\\\"
        )
    lines += [r"\hline", r"\end{tabular}"]
    (TEX / "fase1_comparacao.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    nums = [
        r"% Macros da v2; gerado por scripts/v3_gerar_saidas.py",
        rf"\newcommand{{\vdoisLinhasInconclusivas}}{{{sum(1 for r in rows if r['decisao'] == 'inconclusivo')}}}",
        rf"\newcommand{{\vdoisLinhasAumento}}{{{sum(1 for r in rows if r['decisao'] == 'aumento')}}}",
        rf"\newcommand{{\vdoisLinhasReducao}}{{{sum(1 for r in rows if r['decisao'] == 'reducao')}}}",
    ]
    (TEX / "numeros_v2.tex").write_text("\n".join(nums) + "\n", encoding="utf-8")


if __name__ == "__main__":
    heatmap()
    tabela_baselines()
    tabela_inferencia()
    print("saídas geradas")
    sys.exit(0)
