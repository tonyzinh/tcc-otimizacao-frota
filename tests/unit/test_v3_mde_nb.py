from datetime import date, timedelta

import numpy as np
import pytest

from tcc_frota.v3 import inferencia as inf
from tcc_frota.v3.mde_nb import mde_rows


def _pairs(d_served, d_empty, n=16):
    dates = tuple(date(2026, 3, 16) + timedelta(days=i) for i in range(n))
    zeros = np.zeros(n)
    base = {k: zeros.copy() for k in inf.FIELDS}
    base["served"], base["empty_km"] = np.full(n, 100.0), np.full(n, 300.0)
    plan = {k: v.copy() for k, v in base.items()}
    plan["served"], plan["empty_km"] = base["served"] + d_served, base["empty_km"] + d_empty
    return inf.Pairs(("mar2026", "04-11", "B", "x"), dates, base, plan)


def test_mde_nb_zero_quando_plano_igual_ao_baseline():
    rows = mde_rows({("mar2026", "04-11", "B", "x"): _pairs(np.zeros(16), np.zeros(16))}, "T", reps=200, e_values=(5, 30))
    assert [r["e_star_km_por_corrida"] for r in rows] == [5, 30]
    assert all(r["mde_nb_pior_variante"] == 0 and r["nb_corridas_equiv_dia"] == 0 for r in rows)


def test_mde_nb_e_z_vezes_erro_padrao_e_nb_bate_com_formula():
    rng = np.random.default_rng(1)
    ds, de = rng.normal(2, 3, 16), rng.normal(30, 10, 16)
    (row,) = mde_rows({("mar2026", "04-11", "B", "x"): _pairs(ds, de)}, "T", reps=500, e_values=(10,))
    assert row["mde_nb_iid"] == pytest.approx(inf.mde(row["se_iid"]))
    assert row["mde_nb_pior_variante"] >= row["mde_nb_iid"] - 1e-12
    assert row["nb_corridas_equiv_dia"] == pytest.approx(ds.mean() - de.mean() / 10)
    assert row["ic_decisao_inf"] <= row["nb_corridas_equiv_dia"] <= row["ic_decisao_sup"]
