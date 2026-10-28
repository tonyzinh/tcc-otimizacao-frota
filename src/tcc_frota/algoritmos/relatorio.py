"""Tabelas finais da bateria: critérios por algoritmo, fronteira de Pareto e LaTeX (gerado, não editado).

Lê só arquivos de `resultados/` produzidos pelas execuções registradas; não recalcula nada do zero.
"""

from __future__ import annotations

import json
from pathlib import Path

from tcc_frota.algoritmos.estatistica import criteria
from tcc_frota.algoritmos.protocolo import MONTH_LABEL, RESULTS, read_rows, write_rows

TABLES = Path("tabelas")
LABELS = {
    "ref_proporcional": "Proporcional (artigo)",
    "ref_guloso_a0.05": "Guloso α=0,05 (artigo)",
    "ref_guloso_a0.2": "Guloso α=0,2 (artigo)",
    "ref_guloso_a0.5": "Guloso α=0,5 (artigo)",
    "ref_regra_limiar": "Regra de limiar (artigo)",
    "fin_fluxo_custo_minimo": "5.1 Fluxo de custo mínimo",
    "fin_hungaro": "5.2 Húngaro",
    "fin_milp": "5.3 MILP min(B+R)",
    "fin_busca_local": "5.4 LNS",
    "fin_recozimento": "5.5 Recozimento simulado",
    "fin_nsga2": "5.6 NSGA-II",
    "fin_robusto_cenarios": "5.7 Robusto por cenários",
    "fin_pso": "5.8 PSO",
}


def _f(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def load_month(period: str) -> dict[tuple[str, str], dict]:
    rows = read_rows(RESULTS / f"finalistas_{MONTH_LABEL[period]}.csv")
    out = {}
    for r in rows:
        out[(r["regime"], r["cenario"])] = {
            k: (_f(v) if k not in ("periodo", "regime", "cenario", "familia", "parametros", "soma_confere_b_mais_r") else v)
            for k, v in r.items()
        }
    return out


def final_table() -> list[dict]:
    months = {p: load_month(p) for p in MONTH_LABEL if (RESULTS / f"finalistas_{MONTH_LABEL[p]}.csv").exists()}
    scen = sorted({c for m in months.values() for (reg, c) in m if reg == "B"}, key=lambda c: list(LABELS).index(c) if c in LABELS else 99)
    out = []
    for c in scen:
        b = {p: m[("B", c)] for p, m in months.items() if ("B", c) in m}
        a = {p: m[("A", c)] for p, m in months.items() if ("A", c) in m}
        holm_p = {p: v["p_km_vazio_por_corrida_holm"] for p, v in b.items()}
        crit = criteria(b, a, holm_p) if len(b) == 2 else {"veredito": "incompleto (falta um mês)"}
        row = {"cenario": c, "algoritmo": LABELS.get(c, c)}
        for p, v in b.items():
            lab = MONTH_LABEL[p]
            for k in ("corridas_atendidas_var_pct", "km_vazio_por_corrida_var_pct"):
                row[f"{lab}_{k}"] = v[k]
                row[f"{lab}_{k}_ic_inf"] = v[k + "_ic_inf"]
                row[f"{lab}_{k}_ic_sup"] = v[k + "_ic_sup"]
            row[f"{lab}_km_vazio_por_corrida"] = v["km_vazio_por_corrida"]
            row[f"{lab}_km_vazio_por_corrida_base"] = v["km_vazio_por_corrida_base"]
            row[f"{lab}_km_busca_por_corrida"] = v["km_busca_por_corrida"]
            row[f"{lab}_km_repos_por_corrida"] = v["km_repos_por_corrida"]
            row[f"{lab}_b_mais_r_confere"] = v["soma_confere_b_mais_r"]
            row[f"{lab}_p_holm"] = v["p_km_vazio_por_corrida_holm"]
            row[f"{lab}_p_bruto"] = v["p_km_vazio_por_corrida"]
            row[f"{lab}_dias_com_reducao"] = f"{int(v['dias_com_reducao'])}/{int(v['dias'])}"
            row[f"{lab}_regime_A_km_vazio_var_pct"] = a.get(p, {}).get("km_vazio_por_corrida_var_pct", float("nan"))
            row[f"{lab}_km_vazio_por_corrida_extra"] = v["km_vazio_incremental_por_corrida_extra"]
            row[f"{lab}_fracao_nao_incremental_equilibrio"] = v["fracao_nao_incremental_equilibrio"]
            row[f"{lab}_tempo_plano_medio_s"] = v["tempo_plano_medio_s"]
            row[f"{lab}_fracao_motoristas_movidos_pct"] = v["fracao_motoristas_movidos_pct"]
            row[f"{lab}_km_medio_por_movimento"] = v["km_medio_por_movimento"]
            row[f"{lab}_tempo_ate_passageiro_dif_s"] = v["tempo_ate_passageiro_dif_s"]
        row.update(crit)
        out.append(row)
    write_rows(RESULTS / "tabela_final_criterios.csv", out)
    return out


def pareto_points() -> list[dict]:
    """Pontos da calibração (todas as configurações registradas e avaliações do NSGA-II) e o baseline."""
    pts = [
        {
            "origem": "baseline",
            "familia": "nenhum",
            "cenario": "sem_reposicionamento",
            "var_corridas_pct": 0.0,
            "var_km_vazio_por_corrida_pct": 0.0,
        }
    ]
    for r in read_rows(RESULTS / "registro_configuracoes.csv"):
        if r["etapa"] == "calibracao":
            pts.append(
                {
                    "origem": "registro",
                    "familia": r["familia"],
                    "cenario": r["cenario"],
                    "var_corridas_pct": _f(r["var_corridas_pct"]),
                    "var_km_vazio_por_corrida_pct": _f(r["var_km_vazio_por_corrida_pct"]),
                }
            )
    nsga = RESULTS / "nsga2_avaliacoes_calibracao.csv"
    if nsga.exists():
        for r in read_rows(nsga):
            base_ride = _f(r["km_vazio_base"]) / _f(r["corridas_base"])
            pts.append(
                {
                    "origem": "nsga2_avaliacao",
                    "familia": "nsga2",
                    "cenario": f"nsga2|s{r['semente']}|{r['avaliacao']}",
                    "var_corridas_pct": 100 * (_f(r["corridas"]) / _f(r["corridas_base"]) - 1),
                    "var_km_vazio_por_corrida_pct": 100 * (_f(r["km_vazio_por_corrida"]) / base_ride - 1),
                }
            )
    for p in pts:  # não dominado: mais corridas e menos km vazio/corrida
        p["nao_dominado"] = not any(
            q["var_corridas_pct"] >= p["var_corridas_pct"]
            and q["var_km_vazio_por_corrida_pct"] <= p["var_km_vazio_por_corrida_pct"]
            and (q["var_corridas_pct"] > p["var_corridas_pct"] or q["var_km_vazio_por_corrida_pct"] < p["var_km_vazio_por_corrida_pct"])
            for q in pts
        )
    write_rows(RESULTS / "fronteira_pareto.csv", pts)
    return pts


def pareto_figure(pts: list[dict]) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#999999", "#000000"]
    fams = sorted({p["familia"] for p in pts if p["familia"] != "nenhum"})
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for k, f in enumerate(fams):
        sel = [p for p in pts if p["familia"] == f]
        ax.scatter(
            [p["var_km_vazio_por_corrida_pct"] for p in sel],
            [p["var_corridas_pct"] for p in sel],
            s=10 if f == "nsga2" else 28,
            alpha=0.35 if f == "nsga2" else 0.85,
            color=colors[k % len(colors)],
            label=f,
        )
    ax.scatter([0], [0], marker="*", s=220, color="black", label="baseline", zorder=5)
    ax.axvline(0, color="grey", lw=0.8, ls="--")
    ax.axhline(-1, color="grey", lw=0.8, ls=":")
    ax.set_xlabel("KM vazio total por corrida: variação vs. baseline (%)")
    ax.set_ylabel("Corridas atendidas: variação vs. baseline (%)")
    ax.set_title("Calibração (2–15/03, regime B, 04–11h): todas as configurações")
    ax.legend(fontsize=7, ncol=2, loc="lower right")
    fig.tight_layout()
    out = RESULTS / "fronteira_pareto.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def _pt(v: float, d: int = 2) -> str:
    return "---" if v != v else f"{v:+.{d}f}".replace(".", "{,}")


def latex(table: list[dict]) -> list[Path]:
    TABLES.mkdir(exist_ok=True)
    lines = [
        r"% Gerado por tcc_frota.algoritmos.relatorio — não editar à mão.",
        r"\begin{tabular}{lrrrrc}",
        r"\hline",
        r"Algoritmo & \multicolumn{2}{c}{Corridas (\%)} & \multicolumn{2}{c}{KM vazio/corrida (\%)} & Aprovado \\",
        r" & mar & set & mar & set & \\",
        r"\hline",
    ]
    for r in table:
        cell = lambda lab, k: (
            f"{_pt(r.get(f'{lab}_{k}', float('nan')))} [{_pt(r.get(f'{lab}_{k}_ic_inf', float('nan')))}; "
            f"{_pt(r.get(f'{lab}_{k}_ic_sup', float('nan')))}]"
        )
        ok = "sim" if r.get("veredito", "").startswith("superior") else "não"
        lines.append(
            f"{r['algoritmo']} & {cell('marco', 'corridas_atendidas_var_pct')} & {cell('setembro', 'corridas_atendidas_var_pct')} & "
            f"{cell('marco', 'km_vazio_por_corrida_var_pct')} & {cell('setembro', 'km_vazio_por_corrida_var_pct')} & {ok} \\\\"
        )
    lines += [r"\hline", r"\end{tabular}"]
    p1 = TABLES / "tab_bateria_principal.tex"
    p1.write_text("\n".join(lines) + "\n", encoding="utf-8")
    yn = lambda b: "sim" if b is True or b == "True" else "não"
    lines = [
        r"% Gerado por tcc_frota.algoritmos.relatorio — não editar à mão.",
        r"\begin{tabular}{lccccc}",
        r"\hline",
        r"Algoritmo & C1 KM vazio & C2 atendimento & C3 simulador & C4 consistência & C5 tempo \\",
        r"\hline",
    ]
    for r in table:
        lines.append(
            f"{r['algoritmo']} & {yn(r.get('c1_km_vazio_menor'))} & {yn(r.get('c2_nao_inferior_atendimento'))} & "
            f"{yn(r.get('c3_reducao_no_simulador'))} & {yn(r.get('c4_consistencia'))} & {yn(r.get('c5_tempo'))} \\\\"
        )
    lines += [r"\hline", r"\end{tabular}"]
    p2 = TABLES / "tab_bateria_criterios.tex"
    p2.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return [p1, p2]


def latex_extras() -> Path | None:
    """Tabela própria dos experimentos fora do escopo D+1 (intradiário e D+0), com o atendimento ao lado."""
    rows = []
    for period, lab in MONTH_LABEL.items():
        path = RESULTS / f"extras_{lab}.csv"
        if path.exists():
            rows += [(lab, r) for r in read_rows(path)]
    if not rows:
        return None
    lines = [
        r"% Gerado por tcc_frota.algoritmos.relatorio — não editar à mão. Fora da tabela principal.",
        r"\begin{tabular}{llrr}",
        r"\hline",
        r"Mês & Experimento & Corridas (\%) & KM vazio/corrida (\%) \\",
        r"\hline",
    ]
    for lab, r in rows:
        c = lambda k: f"{_pt(_f(r[k]))} [{_pt(_f(r[k + '_ic_inf']))}; {_pt(_f(r[k + '_ic_sup']))}]"
        lines.append(
            f"{lab} & {r['rotulo']} ({r['cenario'].removeprefix('fin_')}) & {c('corridas_atendidas_var_pct')} & "
            f"{c('km_vazio_por_corrida_var_pct')} \\\\"
        )
    lines += [r"\hline", r"\end{tabular}"]
    out = TABLES / "tab_bateria_extras.tex"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def build() -> dict:
    table = final_table()
    pts = pareto_points()
    fig = pareto_figure(pts)
    tex = latex(table)
    extra = latex_extras()
    if extra:
        tex.append(extra)
    return {
        "algoritmos": len(table),
        "aprovados": [r["algoritmo"] for r in table if r.get("veredito", "").startswith("superior")],
        "indicios": [r["algoritmo"] for r in table if r.get("veredito") == "indício, não confirmado"],
        "figura": str(fig),
        "latex": [str(p) for p in tex],
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
