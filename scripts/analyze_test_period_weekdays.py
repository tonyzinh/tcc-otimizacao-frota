"""Rodada 8 (análise posterior): tabela dia a dia de 26/10 a 08/11 contra os mesmos dias da semana de outubro.

Só lê agregados já gravados nas rodadas 5 e 7; não lê dados brutos nem simula. Plano em docs/REGISTRO_DECISOES.md, R-31.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
PH = RAIZ / "reports" / "diagnostics"
SAIDA = PH / "availability" / "test_period_weekday_comparison"
SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
FERIADOS = {"2026-10-12": "feriado (N. Sra. Aparecida)", "2026-11-02": "feriado (Finados)"}
LIMITE_QUEDA = 0.80


def _dias(a: str, b: str) -> list[str]:
    return [d.strftime("%Y-%m-%d") for d in pd.date_range(a, b)]


def _atendimento_a() -> pd.DataFrame:
    cols = ["dia", "pedidos", "atendidos"]
    t = pd.read_csv(PH / "calibration" / "recalibration_out_of_sample" / "teste_por_dia.csv")
    s = pd.read_csv(PH / "calibration" / "recalibration_out_of_sample" / "setout_por_dia.csv")
    a = pd.concat([x[(x.variante == "calibracao_nova") & (x.politica == "A")][cols] for x in (t, s)])
    a = a.drop_duplicates("dia").rename(columns={"pedidos": "pedidos_simulados", "atendidos": "atendidos_A"})
    a["atendidos_A_pct"] = 100 * a.atendidos_A / a.pedidos_simulados
    return a


def montar() -> tuple[pd.DataFrame, pd.DataFrame]:
    d = pd.read_csv(PH / "batching" / "global_greedy_comparison" / "dados_por_dia.csv")[
        ["dia", "pedidos_tempo_real", "motoristas_no_registro"]
    ]
    d = d.merge(_atendimento_a(), on="dia", how="left")
    d["dia_semana"] = [SEMANA[date.fromisoformat(x).weekday()] for x in d.dia]
    d["observacao"] = d.dia.map(FERIADOS).fillna("")

    ref_dias = [x for x in _dias("2026-10-01", "2026-10-25") if x not in FERIADOS]
    ref = (
        d[d.dia.isin(ref_dias)]
        .groupby("dia_semana")[["pedidos_tempo_real", "motoristas_no_registro", "atendidos_A", "atendidos_A_pct"]]
        .median()
        .add_prefix("ref_out_")
        .reset_index()
    )
    ref["dias_na_referencia"] = d[d.dia.isin(ref_dias)].groupby("dia_semana").size().reindex(ref.dia_semana).to_numpy()

    teste = d[d.dia.isin(_dias("2026-10-26", "2026-11-08"))].merge(ref, on="dia_semana", how="left")
    teste["pedidos_razao_ref"] = teste.pedidos_tempo_real / teste.ref_out_pedidos_tempo_real
    teste["motoristas_razao_ref"] = teste.motoristas_no_registro / teste.ref_out_motoristas_no_registro
    teste["queda"] = teste.pedidos_razao_ref < LIMITE_QUEDA
    teste["no_teste"] = teste.atendidos_A.notna()
    return teste, ref


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    teste, ref = montar()
    teste.to_csv(SAIDA / "dia_a_dia.csv", index=False)
    ref.to_csv(SAIDA / "referencia_outubro.csv", index=False)
    uteis = teste[teste.dia.isin(_dias("2026-11-03", "2026-11-06"))]
    veredito = "todos com queda" if uteis.queda.all() else ("nenhum com queda" if not uteis.queda.any() else "misto")
    (SAIDA / "criterio.txt").write_text(
        f"limite: pedidos < {LIMITE_QUEDA:.0%} da mediana de outubro no mesmo dia da semana (sem 12/10)\ndias úteis 03-06/11: {veredito}\n",
        encoding="utf-8",
    )
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(
            teste[
                [
                    "dia",
                    "dia_semana",
                    "observacao",
                    "pedidos_tempo_real",
                    "ref_out_pedidos_tempo_real",
                    "pedidos_razao_ref",
                    "motoristas_no_registro",
                    "ref_out_motoristas_no_registro",
                    "atendidos_A",
                    "atendidos_A_pct",
                    "ref_out_atendidos_A_pct",
                    "queda",
                ]
            ].round(3)
        )
        print(ref.round(2))
    print("dias úteis 03-06/11:", veredito)


if __name__ == "__main__":
    main()
