"""Análise dos resultados históricos congelados: totais por política e contrastes pareados (C×A principal; C×B e B×A complementares).

Critérios de serviço (fixados antes das execuções): E1 sem violação de compromisso causada pela política; E2 atendidos(política) >=
atendidos(referência) no período; E3 P90 agregado da espera <= o da referência. A espera é calculada SÓ entre os pedidos atendidos, e
políticas diferentes podem atender conjuntos diferentes de pedidos.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from tcc_frota.metrics.statistics import moving_block_bootstrap, pooled_percentile
from tcc_frota.simulation.historical import POLICY_IDS

POLICY_LABELS = {
    "A": "A · mais próximo livre, despacho imediato",
    "B": "B · mais próximo livre, lotes de 60 s",
    "C": "C · atribuição conjunta (húngaro), lotes de 60 s",
}
CONTRASTS = [("C", "A", "PRINCIPAL"), ("C", "B", "complementar"), ("B", "A", "complementar")]
PERIODS = {"replicacao": "Replicação 16–30/09/2026", "final": "Avaliação final 01–25/10/2026"}


def load_days(folder) -> pd.DataFrame:
    """Concatena os Parquet por dia (``dia=*.parquet``) de uma pasta e mantém só as políticas A, B e C."""
    parts = [pd.read_parquet(f) for f in sorted(Path(folder).glob("dia=*.parquet"))]
    if not parts:
        raise FileNotFoundError(f"sem resultados em {folder}")
    df = pd.concat(parts, ignore_index=True)
    return df[df.config.isin(POLICY_IDS.values())]


def absolute_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Totais do período por política: pedidos, atendidos, km vazio, km por atendido, espera (entre atendidos) e tempo computacional."""
    rows = []
    for key, name in POLICY_IDS.items():
        d = df[df.config == name].sort_values("dia")
        w = np.concatenate([np.asarray(v, float) for v in d.esperas_s])
        requests, served = int(d.pedidos.sum()), int(d.atendidos.sum())
        rows.append(
            {
                "politica": POLICY_LABELS[key],
                "dias": len(d),
                "pedidos_elegiveis": requests,
                "atendidos": served,
                "nao_atendidos": requests - served,
                "atendimento_pct": 100 * served / requests,
                "km_vazio_total": float(d.km_vazio_total.sum()),
                "km_vazio_por_atendido": float(d.km_vazio_total.sum()) / max(served, 1),
                "espera_media_s": float(w.mean()),
                "espera_p90_s": float(np.percentile(w, 90)),
                "violacoes_compromisso_por_politica": int(d.comp_violacao_por_politica.sum()),
                "compromissos_entrada_inconsistente": int(d.comp_entrada_inconsistente.sum()),
                "tempo_computacional_total_s": float(d.tempo_plano_s.sum()),
                "tempo_computacional_por_dia_s": float(d.tempo_plano_s.mean()),
            }
        )
    return pd.DataFrame(rows)


def paired_contrast(df: pd.DataFrame, a: str, b: str, role: str) -> dict:
    """Contraste pareado por dia da política `a` contra a referência `b` (chaves "A", "B" ou "C").

    A variação de km vazio é ``a - b``: NEGATIVO = REDUÇÃO. A diferença de atendimento em pontos percentuais usa o universo elegível
    (``pedidos``) como denominador; a variação relativa dos atendidos usa o total atendido de `b`.
    """
    x = df[df.config == POLICY_IDS[a]].sort_values("dia").reset_index(drop=True)
    r = df[df.config == POLICY_IDS[b]].sort_values("dia").reset_index(drop=True)
    assert list(x.dia) == list(r.dia), "dias diferentes"
    dkm = (x.km_vazio_total - r.km_vazio_total).to_numpy()
    lo, hi = moving_block_bootstrap(dkm)
    dat = (x.atendidos - r.atendidos).to_numpy()
    alo, ahi = moving_block_bootstrap(dat.astype(float))
    kx, kr = float(x.km_vazio_total.sum()), float(r.km_vazio_total.sum())
    requests = int(x.pedidos.sum())
    wx = np.concatenate([np.asarray(v, float) for v in x.esperas_s])
    wr = np.concatenate([np.asarray(v, float) for v in r.esperas_s])
    viol = int(x.comp_violacao_por_politica.sum())
    e1 = viol == 0
    e2 = int(x.atendidos.sum()) >= int(r.atendidos.sum())
    e3 = float(np.percentile(wx, 90)) <= float(np.percentile(wr, 90)) + 1e-9
    preserved = bool(e1 and e2 and e3)
    served_diff = int(x.atendidos.sum() - r.atendidos.sum())
    cls = "sem_reducao_detectavel"
    if hi < 0:
        cls = "reducao_com_servico_preservado" if preserved else "reducao_sem_servico_preservado"
    return {
        "contraste": f"{a} × {b}",
        "papel": role,
        "dias": len(x),
        f"km_vazio_{a}": kx,
        f"km_vazio_{b}": kr,
        "variacao_km_vazio_km (negativo = reducao)": kx - kr,
        "variacao_km_vazio_pct (negativo = reducao)": 100 * (kx - kr) / kr,
        "diferenca_media_diaria_km": float(dkm.mean()),
        "ic95_diferenca_media_diaria_km": [lo, hi],
        "dias_com_melhora": int((dkm < -1e-9).sum()),
        "dias_com_piora": int((dkm > 1e-9).sum()),
        "dias_iguais": int((np.abs(dkm) <= 1e-9).sum()),
        "diferenca_atendidos": served_diff,
        "diferenca_atendimento_pontos_percentuais": 100 * served_diff / requests,
        "variacao_relativa_atendidos_pct_da_referencia": 100 * served_diff / int(r.atendidos.sum()),
        "ic95_diferenca_media_diaria_atendidos": [alo, ahi],
        "diferenca_nao_atendidos": int((x.pedidos - x.atendidos).sum() - (r.pedidos - r.atendidos).sum()),
        "diferenca_espera_media_s": float(wx.mean() - wr.mean()),
        "diferenca_espera_p90_s": pooled_percentile(x.esperas_s) - pooled_percentile(r.esperas_s),
        "E1_sem_violacoes": e1,
        "E2_atendimento_preservado": e2,
        "E3_p90_nao_piorou": e3,
        "servico_preservado": preserved,
        "classe": cls,
    }


def to_markdown(df: pd.DataFrame, decimals: int = 2) -> str:
    """Tabela Markdown de um DataFrame com listas formatadas como intervalos."""
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    lines = []
    for _, row in df.iterrows():
        cells = []
        for v in row:
            if isinstance(v, float):
                cells.append(f"{v:,.{decimals}f}")
            elif isinstance(v, list):
                cells.append("(" + "; ".join(f"{y:,.{decimals}f}" for y in v) + ")")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join([head, sep, *lines])
