"""Testes da estatística pareada (bootstrap por blocos, Holm, P90 agregado)."""

from __future__ import annotations

import numpy as np
import pytest

from tcc_frota.metrics import statistics as st


def test_moving_block_bootstrap_is_reproducible_when_seed_is_fixed():
    x = np.arange(20, dtype=float)
    assert st.moving_block_bootstrap(x, n=200) == st.moving_block_bootstrap(x, n=200)


def test_moving_block_bootstrap_returns_nan_when_series_is_empty():
    lo, hi = st.moving_block_bootstrap(np.array([]))
    assert np.isnan(lo) and np.isnan(hi)


def test_moving_block_bootstrap_interval_contains_mean_when_series_is_constant():
    lo, hi = st.moving_block_bootstrap(np.full(15, -3.0), n=100)
    assert lo == pytest.approx(-3.0) and hi == pytest.approx(-3.0)


def test_holm_adjust_is_monotone_and_not_below_raw_p_when_several_tests_are_given():
    p = [0.01, 0.04, 0.03]
    adj = st.holm_adjust(p)
    assert all(a >= b for a, b in zip(adj, p, strict=True))
    assert adj[0] == pytest.approx(0.03)  # 3 * 0.01
    assert max(adj) <= 1.0


def test_seed_bootstrap_p_has_floor_of_one_over_resamples_when_effect_is_unanimous():
    lo, hi, p = st.seed_bootstrap(np.full(30, -1.0), n=500)
    assert hi < 0 and p == pytest.approx(1 / 500)


def test_pooled_percentile_uses_all_waits_when_days_have_different_sizes():
    assert st.pooled_percentile([[0.0, 10.0], [20.0, 30.0, 40.0]], 50) == pytest.approx(20.0)
