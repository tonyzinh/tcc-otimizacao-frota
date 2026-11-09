"""Recalcula os números derivados citados no artigo que antes vinham de scripts locais da sessão (rodada 6) e confere o texto.

Origem: na rodada 6 (09/11/2026), os valores abaixo foram calculados por scripts locais da sessão (`share.py` e `dn_dia.py`), que não
ficaram no repositório. Este script os recalcula **a partir dos dados por dia** gravados pelos scripts versionados (sem simulação nova)
e confere se o valor arredondado aparece no texto do artigo (`article/sections` e `article/appendices`):

- km vazio por dia em A e C, a redução por dia e a participação do km vazio no km total modelado (setembro e outubro, configuração
  congelada) e a queda dessa participação em pontos percentuais (Seção 4, "Significado prático"; Resumo; Conclusão);
- expirados depois de ter tido veículo elegível em B e C (preterição; Seção 4);
- diferença de atendidos por dia, C − A, no treino (janela de 60 s), em setembro e em outubro (Seção 4.2);
- redução de km de C contra A como % do km total modelado de A no teste fora da amostra (Apêndice B).

Cada valor também é comparado com o resumo gravado pelo script de origem, quando existe, para detectar divergência entre o dado por dia
e o resumo. Saída: `reports/diagnostics/consistency/article_derived_values/derived_values.csv`.

    python scripts/compute_article_derived_values.py           # recalcula, grava e confere
    python scripts/compute_article_derived_values.py --check   # só confere (usado nos testes); não grava
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R4 = ROOT / "reports/diagnostics/statistics/robustness_review"
R5 = ROOT / "reports/diagnostics/calibration/recalibration_out_of_sample"
OUT = ROOT / "reports/diagnostics/consistency/article_derived_values/derived_values.csv"
ARTICLE = ROOT / "article"


def br(x: float, nd: int, sinal: bool = False) -> str:
    """Formato do artigo: vírgula decimal, ponto de milhar, sinal de menos tipográfico."""
    s = f"{x:+,.{nd}f}" if sinal else f"{x:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def article_text() -> str:
    parts = [p.read_text(encoding="utf-8") for p in sorted(ARTICLE.glob("sections/*.tex")) + sorted(ARTICLE.glob("appendices/*.tex"))]
    # o LaTeX escreve "\%" e "~"; normaliza para a busca do número
    return re.sub(r"\s+", " ", "\n".join(parts).replace("\\%", "%").replace("~", " "))


def compute() -> list[dict]:
    rows: list[dict] = []

    def add(chave: str, valor: float, texto: str, fonte: str, resumo: float | None = None) -> None:
        rows.append({"chave": chave, "valor": valor, "no_artigo": texto, "fonte": fonte, "valor_no_resumo": resumo})

    # 1. setembro e outubro, configuração congelada (variante base): dados por dia do script da rodada 4
    base = pd.read_csv(R4 / "base_por_dia.csv")
    base = base[base.variante == "base"]
    resumo4 = pd.read_csv(R4 / "base_pratica_e_justica.csv").set_index(["periodo", "politica"])
    for per in ("setembro", "outubro"):
        g = base[base.periodo == per].groupby("politica")
        dias = base[base.periodo == per].dia.nunique()
        km = g.km_vazio.sum()
        share = 100 * km / (km + g.km_com_passageiro.sum())
        f4 = "reports/diagnostics/statistics/robustness_review/base_por_dia.csv"
        for pol in ("A", "C"):
            add(f"{per}_{pol}_km_vazio_por_dia", km[pol] / dias, br(km[pol] / dias, 1), f4, resumo4.loc[(per, pol), "km_vazio_por_dia"])
            add(
                f"{per}_{pol}_km_vazio_sobre_total_pct",
                share[pol],
                br(share[pol], 1) + "%",
                f4,
                resumo4.loc[(per, pol), "km_vazio_sobre_total_modelado_pct"],
            )
        add(f"{per}_CxA_km_vazio_evitado_por_dia", (km["A"] - km["C"]) / dias, br((km["A"] - km["C"]) / dias, 1), f4)
        add(f"{per}_CxA_queda_participacao_pp", share["A"] - share["C"], br(share["A"] - share["C"], 1), f4)
        for pol in ("B", "C"):
            v = base[(base.periodo == per) & (base.politica == pol)].preteridos_e_expirados.sum()
            add(f"{per}_{pol}_preteridos_e_expirados", v, br(v, 0), f4, resumo4.loc[(per, pol), "preteridos_e_expirados"])
        aten = base[base.periodo == per].pivot_table(index="dia", columns="politica", values="atendidos", aggfunc="sum")
        dn = (aten.C - aten.A).mean()
        add(f"{per}_CxA_atendidos_por_dia", dn, br(dn, 1, sinal=True), f4)

    # 2. treino, janela de 60 s (a adotada): dados por dia do script da rodada 4
    jt = pd.read_csv(R4 / "janelas_treino_por_dia.csv")
    jt = jt[jt.variante == "janela_60s"].pivot_table(index="dia", columns="politica", values="atendidos", aggfunc="sum")
    resumo_j = pd.read_csv(R4 / "janelas_treino_resumo.csv").set_index("variante")
    dn = (jt.C - jt.A).mean()
    add(
        "treino_janela60s_CxA_atendidos_por_dia",
        dn,
        br(dn, 1, sinal=True),
        "reports/diagnostics/statistics/robustness_review/janelas_treino_por_dia.csv",
        resumo_j.loc["janela_60s", "CxA_dN"] / len(jt),
    )

    # 3. teste fora da amostra (calibração nova, 12 dias elegíveis): dados por dia do script da rodada 5
    te = pd.read_csv(R5 / "teste_por_dia.csv")
    te = te[te.variante == "calibracao_nova"]
    g = te.groupby("politica")
    tot_a = g.km_vazio.sum()["A"] + g.km_com_passageiro.sum()["A"]
    v = 100 * (g.km_vazio.sum()["A"] - g.km_vazio.sum()["C"]) / tot_a
    r5 = pd.read_csv(R5 / "teste_resumo.csv")
    r5 = r5[(r5.variante == "calibracao_nova") & (r5.periodo == "26/10-08/11")].iloc[0]
    add(
        "teste_CxA_reducao_pct_do_km_total_de_A",
        v,
        br(v, 2) + "%",
        "reports/diagnostics/calibration/recalibration_out_of_sample/teste_por_dia.csv",
        r5["CxA_reducao_pp_do_km_total_de_A"],
    )
    add(
        "teste_dias",
        te.dia.nunique(),
        str(te.dia.nunique()),
        "reports/diagnostics/calibration/recalibration_out_of_sample/teste_por_dia.csv",
    )
    return rows


def check(rows: list[dict]) -> list[str]:
    txt = article_text()
    problems = []
    for r in rows:
        if r["valor_no_resumo"] is not None and pd.notna(r["valor_no_resumo"]) and abs(r["valor"] - float(r["valor_no_resumo"])) > 1e-6:
            problems.append(f"{r['chave']}: dado por dia {r['valor']} difere do resumo {r['valor_no_resumo']}")
        if not re.search(r"(?<![\d,.])" + re.escape(r["no_artigo"]) + r"(?![\d])", txt):
            problems.append(f"{r['chave']}: '{r['no_artigo']}' não encontrado no artigo")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="só confere; não grava")
    a = ap.parse_args()
    rows = compute()
    problems = check(rows)
    for r in rows:
        r["encontrado_no_artigo"] = not any(p.startswith(r["chave"] + ":") and "não encontrado" in p for p in problems)
        print(f"{r['chave']:45s} {r['valor']:>14.6f}  artigo: {r['no_artigo']:>10s}  {'ok' if r['encontrado_no_artigo'] else 'AUSENTE'}")
    if not a.check:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(OUT, index=False)
        print("gravado:", OUT.relative_to(ROOT))
    for p in problems:
        print("PROBLEMA:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
