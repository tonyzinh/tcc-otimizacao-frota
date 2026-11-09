"""Análise pareada do experimento sintético: cada política em lote contra A (e o Húngaro contra o mais próximo na mesma janela).

A unidade é a semente. Critério de serviço SINTÉTICO (fixado antes, em docs/PLANO_GULOSO_LIQUIDO.md): razão média pareada de atendidos
>= 0,995 E razão das médias de P90 <= 1,05. NÃO é igual ao E2 dos dados históricos (atendidos(C) >= atendidos(ref), sem tolerância).
Os Parquet congelados chamam A de ``R0``; aqui é renomeado para ``A``.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from tcc_frota.metrics.statistics import holm_adjust, seed_bootstrap

MIN_SERVED_RATIO = 0.995
MAX_P90_RATIO = 1.05
SERVED_GAIN_RATIO = 1.005
CONFIRMATORY_SCENARIOS = ("S1", "S2", "S3", "S4", "S5")


def load_scenarios(folder) -> pd.DataFrame:
    """Concatena ``cen=*.parquet`` de uma pasta e renomeia a política R0 (nome gravado) para A."""
    df = pd.concat([pd.read_parquet(f) for f in sorted(Path(folder).glob("cen=*.parquet"))], ignore_index=True)
    df["politica"] = df.politica.replace({"R0": "A"})
    return df


def classify(lo: float, hi: float, preserved: bool, served_ratio: float) -> str:
    """Classe do contraste de km vazio dado o IC95% e a preservação do serviço (critério sintético)."""
    if hi < 0:
        return "reducao_com_servico_preservado" if preserved else "menos_km_com_pior_atendimento"
    if lo > 0:
        return "mais_atendimento_com_mais_km" if served_ratio >= SERVED_GAIN_RATIO else "piora_sem_compensacao"
    return "sem_diferenca_detectavel"


def paired_contrast(a: pd.DataFrame, b: pd.DataFrame) -> dict:
    """Diferença pareada ``b - a`` por semente (ambos indexados por semente). Negativo em km = redução."""
    d = (b.km_vazio_total - a.km_vazio_total).to_numpy()
    lo, hi, p = seed_bootstrap(d)
    served_ratio = float((b.atendidos / a.atendidos).mean())
    p90_ratio = float(b.espera_p90_s.mean() / a.espera_p90_s.mean())
    preserved = served_ratio >= MIN_SERVED_RATIO and p90_ratio <= MAX_P90_RATIO
    return {
        "n_sementes": len(d),
        "km_ref_medio": float(a.km_vazio_total.mean()),
        "d_km_medio": float(d.mean()),
        "d_km_dp": float(d.std(ddof=1)) if len(d) > 1 else float("nan"),
        "ic95_inf": lo,
        "ic95_sup": hi,
        "p_boot": p,
        "d_pct": 100 * float(d.mean()) / float(a.km_vazio_total.mean()),
        "freq_melhora": float((d < -1e-9).mean()),
        "freq_piora": float((d > 1e-9).mean()),
        "freq_empate": float((np.abs(d) <= 1e-9).mean()),
        "razao_atendidos": served_ratio,
        "razao_p90": p90_ratio,
        "servico_preservado": preserved,
        "classe": classify(lo, hi, preserved, served_ratio),
    }


def summarize(df: pd.DataFrame, confirmatory: tuple[str, ...] = CONFIRMATORY_SCENARIOS) -> pd.DataFrame:
    """Contrastes de cada política em lote contra A e do Húngaro contra o mais próximo (mesma janela), por cenário.

    Os testes confirmatórios (política em lote × A nos cenários principais) recebem p ajustado por Holm; o restante é exploratório.
    """
    rows = []
    for scenario, g in df.groupby("cenario", sort=False):
        by_policy = {p: x.set_index("semente").sort_index() for p, x in g.groupby("politica")}
        pairs = [(p, "A") for p in by_policy if p != "A"]
        pairs += [(p, p.replace("hungaro", "guloso_fifo")) for p in by_policy if p.startswith("D_") and p.endswith("hungaro")]
        for pol, ref in pairs:
            if ref in by_policy:
                rows.append({"cenario": scenario, "politica": pol, "referencia": ref, **paired_contrast(by_policy[ref], by_policy[pol])})
    table = pd.DataFrame(rows)
    table["p_holm_confirmatorio"] = np.nan
    table["familia"] = ""
    is_batch = table.politica.map(lambda s: bool(re.match(r"D_lote\d+s_(hungaro|fluxo)$", s)))
    family = table[table.cenario.isin(confirmatory) & (table.referencia == "A") & is_batch]
    if len(family):
        table.loc[family.index, "p_holm_confirmatorio"] = holm_adjust(list(family.p_boot))
        table.loc[family.index, "familia"] = "D"
    return table
