"""Regressão: a análise reorganizada reproduz as tabelas congeladas (exige os Parquet locais; senão, pula)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tcc_frota.metrics import historical as h
from tcc_frota.metrics import synthetic as s

ROOT = Path(__file__).resolve().parents[2]
HIST = ROOT / "reports" / "historical" / "frozen_evaluation"
SYNTH = ROOT / "reports" / "synthetic" / "dispatch_evaluation"


@pytest.mark.parametrize("period", ["replicacao", "final"])
def test_historical_totals_match_frozen_tables_when_parquet_is_available(period):
    folder = HIST / "execucao" / "grupo_B" / period
    if not list(folder.glob("dia=*.parquet")):
        pytest.skip("Parquet históricos congelados ausentes (dados locais)")
    new = h.absolute_totals(h.load_days(folder))
    old = pd.read_csv(HIST / "analise" / f"{period}_absolutos.csv")
    assert new.atendidos.tolist() == old.atendidos.tolist()
    assert np.allclose(new.km_vazio_total, old.km_vazio_total)


@pytest.mark.parametrize("period", ["replicacao", "final"])
def test_historical_contrasts_match_frozen_json_when_parquet_is_available(period):
    folder = HIST / "execucao" / "grupo_B" / period
    if not list(folder.glob("dia=*.parquet")):
        pytest.skip("Parquet históricos congelados ausentes (dados locais)")
    df = h.load_days(folder)
    old = json.loads((HIST / "analise" / f"{period}_contrastes.json").read_text(encoding="utf-8"))
    old = old if isinstance(old, list) else list(old.values())
    key = "variacao_km_vazio_pct (negativo = reducao)"
    for a, b, role in h.CONTRASTS:
        new = h.paired_contrast(df, a, b, role)
        ref = next(x for x in old if x["contraste"] == new["contraste"])
        assert new[key] == pytest.approx(ref[key], abs=1e-6)
        assert new["classe"] == ref["classe"]


def test_synthetic_summary_matches_frozen_csv_when_parquet_is_available():
    if not list(SYNTH.glob("cen=*.parquet")):
        pytest.skip("Parquet sintéticos congelados ausentes")
    new = s.summarize(s.load_scenarios(SYNTH))
    old = pd.read_csv(SYNTH / "analise" / "resumo_contrastes.csv")
    m = new.merge(old, on=["cenario", "politica", "referencia"], suffixes=("", "_o"))
    assert len(m) > 0
    assert np.allclose(m.d_km_medio, m.d_km_medio_o) and np.allclose(m.d_pct, m.d_pct_o)
    assert (m.classe == m.classe_o).all()
