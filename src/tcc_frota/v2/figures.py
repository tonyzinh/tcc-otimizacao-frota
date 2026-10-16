"""Figuras do capítulo de resultados, geradas só a partir das tabelas agregadas (CSV).

Rótulos em português, paleta Okabe–Ito (segura para daltonismo) e marcadores/traços distintos para
leitura em preto e branco. Requer o extra opcional `matplotlib` (e `h3` para o mapa).
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

COLORS = {"preto": "#000000", "laranja": "#E69F00", "azul": "#0072B2", "verde": "#009E73",
          "vermelho": "#D55E00", "rosa": "#CC79A7", "ceu": "#56B4E9", "amarelo": "#F0E442"}
REGIME_STYLE = {"A": ("--", "s", COLORS["laranja"], "A: D+1 estrito"),
                "B": ("-", "o", COLORS["azul"], "B: escala conhecida"),
                "C": (":", "^", COLORS["verde"], "C: oráculo (diagnóstico)")}
PERIOD_LABEL = {"mar2026": "março/2026", "set2026": "setembro/2026"}


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for r in rows:
        for k, v in r.items():
            try:
                r[k] = float(v)
            except (TypeError, ValueError):
                pass
    return rows


def _setup():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.alpha": 0.3, "figure.dpi": 100})
    return plt


def _save(fig, out: Path, name: str) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    files = []
    for ext in ("png", "svg"):
        path = out / f"{name}.{ext}"
        fig.savefig(path, dpi=200 if ext == "png" else None, bbox_inches="tight")
        files.append(path.name)
    return files


def fig_demand_by_hour(tables: Path, out: Path) -> list[str]:
    plt = _setup()
    rows = _read(tables / "tab03_demanda_por_hora.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), sharey=True)
    for ax, period in zip(axes, PERIOD_LABEL):
        sel = [r for r in rows if r["periodo"] == period]
        hours = [int(r["hora"]) for r in sel]
        ax.bar(hours, [r["pedidos_por_dia"] for r in sel], color="#BBBBBB", edgecolor="black", linewidth=0.4,
               label="pedidos imediatos/dia")
        ax.bar(hours, [r["aceitos_por_dia"] for r in sel], color=COLORS["azul"], hatch="//", edgecolor="black",
               linewidth=0.4, label="aceitos/dia")
        ax2 = ax.twinx()
        ax2.plot(hours, [r["aceite_pct"] for r in sel], color=COLORS["vermelho"], marker="o", ms=3, label="aceite (%)")
        ax2.set_ylim(0, 100)
        ax2.set_ylabel("aceite (%)")
        ax2.grid(False)
        ax.axvspan(3.5, 10.5, color=COLORS["amarelo"], alpha=0.15)
        ax.set_title(PERIOD_LABEL[period])
        ax.set_xlabel("hora local")
        ax.set_xticks(range(0, 24, 2))
    axes[0].set_ylabel("pedidos por dia")
    handles = axes[0].get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0]
    labels = axes[0].get_legend_handles_labels()[1] + ax2.get_legend_handles_labels()[1]
    fig.legend(handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.08), frameon=False)
    fig.suptitle("Figura 1 – Demanda imediata e aceite por hora (faixa sombreada: janela 04–11h)", y=1.02)
    return _save(fig, out, "fig01_demanda_aceite_por_hora")


def fig_unserved_map(tables: Path, out: Path) -> list[str]:
    plt = _setup()
    import h3
    from matplotlib.collections import PolyCollection
    from matplotlib import cm, colors

    rows = _read(tables / "tab17_nao_atendidas_por_zona.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
    for ax, period in zip(axes, PERIOD_LABEL):
        sel = [r for r in rows if r["periodo"] == period and r["pedidos"] >= 1]
        polys = [[(lon, lat) for lat, lon in h3.cell_to_boundary(r["h3_r7"])] for r in sel]
        vals = [r["nao_atendidas"] for r in sel]
        norm = colors.Normalize(vmin=0, vmax=max(vals) if vals else 1)
        coll = PolyCollection(polys, array=vals, cmap="Greys", norm=norm, edgecolor="#555555", linewidth=0.3)
        ax.add_collection(coll)
        ax.autoscale_view()
        ax.set_aspect("equal")
        ax.set_xlabel("longitude")
        ax.set_ylabel("latitude")
        ax.set_title(f"{PERIOD_LABEL[period]}: não aceitas, 04–11h")
        fig.colorbar(coll, ax=ax, shrink=0.8, label="pedidos não aceitos no mês")
    fig.suptitle("Figura 2 – Pedidos imediatos não aceitos por zona H3 r7", y=1.0)
    return _save(fig, out, "fig02_nao_atendidas_por_zona")


def fig_forecast(tables: Path, out: Path) -> list[str]:
    plt = _setup()
    rows = _read(tables / "tab18_previsto_observado_diario.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))
    styles = {"media_dia_semana": ("-", "o", COLORS["azul"], "média do mesmo dia da semana"),
              "naive_sazonal": ("--", "s", COLORS["laranja"], "naïve sazonal (D+1−7)"),
              "poisson": (":", "^", COLORS["verde"], "regressão de Poisson")}
    for ax, period in zip(axes, PERIOD_LABEL):
        sel = [r for r in rows if r["periodo"] == period and r["janela"] == "04-11"]
        dates = sorted({r["data"] for r in sel})
        obs = {r["data"]: r["observado"] for r in sel}
        ax.plot(range(len(dates)), [obs[d] for d in dates], color="black", lw=2, label="observado")
        for model, (ls, mk, c, label) in styles.items():
            pred = {r["data"]: r["previsto"] for r in sel if r["modelo"] == model}
            ax.plot(range(len(dates)), [pred.get(d, float("nan")) for d in dates], ls=ls, marker=mk, ms=3, color=c, label=label)
        ax.set_xticks(range(0, len(dates), 5))
        ax.set_xticklabels([dates[i][5:] for i in range(0, len(dates), 5)])
        ax.set_title(PERIOD_LABEL[period])
        ax.set_ylabel("pedidos na janela 04–11h")
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("Figura 3 – Demanda prevista no corte (20h de D) × observada em D+1", y=1.02)
    return _save(fig, out, "fig03_previsto_observado")


def fig_pareto(tables: Path, out: Path) -> list[str]:
    plt = _setup()
    rows = _read(tables / "tab16_fronteira_pareto.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, period in zip(axes, PERIOD_LABEL):
        for regime, (ls, mk, c, label) in REGIME_STYLE.items():
            sel = [r for r in rows if r["periodo"] == period and r["regime"] == regime and str(r["cenario"]).startswith("guloso")]
            sel.sort(key=lambda r: json.loads(r["parametros"])["alpha"])
            x = [r["km_vazio_por_corrida_var_pct"] for r in sel]
            y = [r["corridas_atendidas_var_pct"] for r in sel]
            xerr = [[r["km_vazio_por_corrida_var_pct"] - r["km_vazio_por_corrida_var_pct_ic_inf"] for r in sel],
                    [r["km_vazio_por_corrida_var_pct_ic_sup"] - r["km_vazio_por_corrida_var_pct"] for r in sel]]
            yerr = [[r["corridas_atendidas_var_pct"] - r["corridas_atendidas_var_pct_ic_inf"] for r in sel],
                    [r["corridas_atendidas_var_pct_ic_sup"] - r["corridas_atendidas_var_pct"] for r in sel]]
            ax.errorbar(x, y, xerr=xerr, yerr=yerr, ls=ls, marker=mk, color=c, ms=4, lw=1, elinewidth=0.6,
                        capsize=1.5, label=f"guloso marginal, {label}")
            if regime == "B":
                for r in sel:
                    ax.annotate(f"α={json.loads(r['parametros'])['alpha']:g}", (r["km_vazio_por_corrida_var_pct"],
                                r["corridas_atendidas_var_pct"]), fontsize=6, xytext=(3, 3), textcoords="offset points")
            for name, mk2, c2, lab in (("proporcional", "D", COLORS["vermelho"], "proporcional"),
                                       ("regra_limiar", "P", COLORS["rosa"], "regra de limiar")):
                p = [r for r in rows if r["periodo"] == period and r["regime"] == regime and r["cenario"] == name]
                if p and regime == "B":
                    ax.plot(p[0]["km_vazio_por_corrida_var_pct"], p[0]["corridas_atendidas_var_pct"], marker=mk2,
                            color=c2, ls="none", ms=6, label=f"{lab} (B)")
        ax.axhline(0, color="black", lw=0.8)
        ax.axvline(0, color="black", lw=0.8)
        ax.set_title(PERIOD_LABEL[period] + " (teste, 04–11h)")
        ax.set_xlabel("variação do KM vazio por corrida (%)")
    axes[0].set_ylabel("variação de corridas atendidas (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.14), frameon=False, fontsize=8)
    fig.suptitle("Figura 4 – Fronteira corridas extras × KM vazio por corrida (IC 95% por bootstrap de dias)", y=1.02)
    return _save(fig, out, "fig04_fronteira_pareto")


def fig_by_hour(tables: Path, out: Path) -> list[str]:
    plt = _setup()
    rows = _read(tables / "tab12_por_faixa_horaria.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.2), sharey=True)
    scen = sorted({r["cenario"] for r in rows})
    style = {s: (COLORS["azul"] if s.startswith("guloso") else COLORS["vermelho"] if s == "proporcional" else COLORS["rosa"],
                 "//" if s.startswith("guloso") else "" if s == "proporcional" else "..") for s in scen}
    for ax, period in zip(axes, PERIOD_LABEL):
        width = 0.8 / len(scen)
        for i, s in enumerate(scen):
            sel = [r for r in rows if r["periodo"] == period and r["cenario"] == s]
            ax.bar([r["hora"] + (i - (len(scen) - 1) / 2) * width for r in sel], [r["corridas_extras"] for r in sel],
                   width=width, color=style[s][0], hatch=style[s][1], edgecolor="black", linewidth=0.4,
                   label=s.replace("_", " "))
        ax.axhline(0, color="black", lw=0.8)
        ax.set_title(PERIOD_LABEL[period] + " (teste, regime B)")
        ax.set_xlabel("hora local")
    axes[0].set_ylabel("corridas extras (soma dos dias de teste)")
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("Figura 5 – Efeito do reposicionamento por faixa horária", y=1.02)
    return _save(fig, out, "fig05_efeito_por_hora")


def fig_ladder(tables: Path, out: Path) -> list[str]:
    plt = _setup()
    rows = _read(tables / "tab15_escada_informacao.csv")
    rows = [r for r in rows if str(r["cenario"]).startswith("guloso")]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.2))
    metrics = (("taxa_execucao_pct", "recomendações executadas (%)"),
               ("corridas_atendidas_var_pct", "variação de corridas atendidas (%)"),
               ("km_vazio_por_corrida_var_pct", "variação do KM vazio por corrida (%)"))
    for ax, (m, label) in zip(axes, metrics):
        for j, period in enumerate(PERIOD_LABEL):
            sel = {r["regime"]: r for r in rows if r["periodo"] == period}
            xs = [k + (j - 0.5) * 0.38 for k in range(3)]
            vals = [sel[g][m] if g in sel else float("nan") for g in "ABC"]
            err = None
            if m + "_ic_inf" in rows[0]:
                err = [[vals[k] - sel[g][m + "_ic_inf"] for k, g in enumerate("ABC")],
                       [sel[g][m + "_ic_sup"] - vals[k] for k, g in enumerate("ABC")]]
            ax.bar(xs, vals, width=0.36, yerr=err, capsize=2, color=[COLORS["azul"], COLORS["laranja"]][j],
                   hatch=["", "//"][j], edgecolor="black", linewidth=0.4, label=PERIOD_LABEL[period])
        ax.set_xticks(range(3))
        ax.set_xticklabels(["A: estrito", "B: escala", "C: oráculo"])
        ax.axhline(0, color="black", lw=0.8)
        ax.set_title(label, fontsize=9)
    axes[1].legend(frameon=False, fontsize=8, loc="upper left")
    fig.suptitle("Figura 6 – Escada de informação (guloso marginal intermediário, 04–11h, teste)", y=1.04)
    return _save(fig, out, "fig06_escada_informacao")


def fig_breakeven(tables: Path, out: Path) -> list[str]:
    plt = _setup()
    rows = [r for r in _read(tables / "tab14_ponto_equilibrio.csv") if r["regime"] == "B"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), sharey=True)
    xs = [i / 20 for i in range(0, 61)]
    palette = [COLORS["azul"], COLORS["laranja"], COLORS["verde"], COLORS["vermelho"], COLORS["rosa"], COLORS["ceu"]]
    for ax, period in zip(axes, PERIOD_LABEL):
        sel = [r for r in rows if r["periodo"] == period and r["km_vazio_incremental_por_corrida_extra"] == r["km_vazio_incremental_por_corrida_extra"]
               and r["corridas_extras_por_dia"] > 0]
        sel.sort(key=lambda r: r["km_vazio_incremental_por_corrida_extra"])
        for i, r in enumerate(sel[:6]):
            e = r["km_vazio_incremental_por_corrida_extra"]
            ax.plot(xs, [e * c for c in xs], color=palette[i % 6], ls=["-", "--", ":", "-."][i % 4],
                    label=f"{r['cenario'].replace('_', ' ')} (e={e:.1f} km)")
        ax.set_title(PERIOD_LABEL[period] + " (regime B)")
        ax.set_xlabel("custo marginal por km (unidade monetária/km; a fornecer)")
    axes[0].set_ylabel("margem mínima por corrida extra")
    axes[0].legend(frameon=False, fontsize=7)
    fig.suptitle("Figura 7 – Ponto de equilíbrio: reposicionar compensa acima da linha (margem > e × custo/km)", y=1.02)
    return _save(fig, out, "fig07_ponto_equilibrio")


def make_figures(tables: Path, out: Path) -> list[str]:
    files = []
    for fn in (fig_demand_by_hour, fig_unserved_map, fig_forecast, fig_pareto, fig_by_hour, fig_ladder, fig_breakeven):
        files += fn(tables, out)
    return files
