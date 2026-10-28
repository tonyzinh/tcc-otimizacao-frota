"""Bloco 2 (exploratório): funções puras do módulo de pickup."""

import math

from tcc_frota.analise import pickup as pk


def test_pickups_keeps_only_dispatch_events():
    trace = [(0.0, "dispatch", "d1", 1, (0, 0), 2.5), (5.0, "move", "d2", None, (0, 0), 1.0), (9.0, "dispatch", "d2", 2, (0, 0), 4.0)]
    assert pk._pickups(trace) == {1: 2.5, 2: 4.0}


def test_summary_reports_median_with_mean_and_empty_is_nan_not_zero():
    s = pk.summary([1.0, 2.0, 3.0, 10.0])
    assert s["n"] == 4 and s["media_km"] == 4.0 and s["mediana_km"] == 2.5 and s["p90_km"] == 3.0
    empty = pk.summary([])
    assert empty["n"] == 0 and all(math.isnan(empty[k]) for k in ("media_km", "mediana_km", "p90_km"))


def test_deciles_are_ordered_and_empty_input_gives_no_values():
    d = pk.deciles([float(x) for x in range(101)])
    assert d == [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0]
    assert pk.deciles([]) == []
