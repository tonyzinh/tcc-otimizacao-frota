"""Bloco 1: WAPE por faixa a partir dos erros por hora e previsões sem dados do dia D nem de D+1."""
from datetime import date, timedelta

from tcc_frota.analise import demanda as dm
from tcc_frota.v2 import forecast as fc


def history(days, value=lambda d, h: 2):
    counts = {(d, h, "z1"): value(d, h) for d in days for h in dm.HOURS}
    return fc.DemandHistory(counts, set(days))


def test_band_and_global_wape_are_sums_of_hourly_errors():
    recs = [{"data": "2026-03-16", "hora": h, "estrato": "alto", "abs_err": float(h), "y": 10.0, "yhat": 9.0} for h in dm.HOURS]
    agg = {r["escopo"]: r for r in dm.aggregate(recs, ["2026-03-16"])}
    assert agg["faixa_04-07"]["wape"] == (4 + 5 + 6) / 30
    assert agg["faixa_10-11"]["wape"] == 10 / 10
    assert agg["global"]["wape"] == sum(dm.HOURS) / 70


def test_models_ignore_target_and_cut_day():
    target = date(2026, 3, 20)
    days = [target - timedelta(days=k) for k in range(0, 70)]
    base = history(days)
    spiked = history(days, lambda d, h: 999 if d >= target - timedelta(days=1) else 2)   # D e D+1 alterados
    cfg = fc.ForecastConfig(excluded_dates=())
    for f in (dm.m0, dm.m1):
        assert f(target, base, cfg) == f(target, spiked, cfg)
    assert dm.m2(target, base, cfg, 0.01) == dm.m2(target, spiked, cfg, 0.01)
