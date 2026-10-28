"""Estatística pareada por dia (Fase 6)."""

import pytest

from tcc_frota.v2 import stats


def day(bs, ps, bk, pk, br=0.0, pr=0.0):
    return {
        "b": {
            "served": bs,
            "pickup_km": bk,
            "reposition_km": br,
            "empty_km": bk + br,
            "wait_sum": 600.0 * bs,
            "n_requests": 100,
            "moves_planned": 0,
            "moves_executed": 0,
        },
        "p": {
            "served": ps,
            "pickup_km": pk,
            "reposition_km": pr,
            "empty_km": pk + pr,
            "wait_sum": 540.0 * ps,
            "n_requests": 100,
            "moves_planned": 4,
            "moves_executed": 2,
        },
    }


def test_sign_flip_exact_and_symmetric():
    assert stats.sign_flip_pvalue([1.0] * 6) == pytest.approx(2 / 64)
    assert stats.sign_flip_pvalue([1.0, -1.0, 1.0, -1.0]) == 1.0
    assert stats.sign_flip_pvalue([]) != stats.sign_flip_pvalue([])  # nan


def test_compare_reports_primary_indicators_with_ci():
    days = [day(50, 52, 100.0, 98.0, pr=10.0), day(40, 41, 80.0, 79.0, pr=8.0), day(60, 63, 120.0, 118.0, pr=12.0)]
    out = stats.compare(days, reps=500)
    assert out["corridas_atendidas_var_pct"] == pytest.approx(100 * (156 / 150 - 1))
    assert out["km_vazio_incremental_por_corrida_extra"] == pytest.approx((325 - 300) / 6)
    assert out["tempo_ate_passageiro_dif_s"] == pytest.approx(-60.0)
    assert out["taxa_execucao_pct"] == pytest.approx(50.0)
    for k in ("corridas_atendidas_var_pct", "km_vazio_por_corrida_var_pct"):
        assert out[k + "_ic_inf"] <= out[k] <= out[k + "_ic_sup"]


def test_bootstrap_is_deterministic():
    days = [day(50 + i, 51 + i, 100.0, 99.0) for i in range(8)]
    assert stats.bootstrap(days, stats.s_served_ratio, 300) == stats.bootstrap(days, stats.s_served_ratio, 300)
