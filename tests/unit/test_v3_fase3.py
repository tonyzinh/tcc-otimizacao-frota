import pytest

from tcc_frota.v3 import analise
from tcc_frota.v3 import avaliacao as av


def test_mix_demand_extremos():
    y = {(5, "a"): 4.0, (6, "b"): 1.0}
    g = {(5, "a"): 1.0, (5, "c"): 3.0}
    assert av.mix_demand(y, g, 0.0) == {(5, "a"): 4.0, (6, "b"): 1.0, (5, "c"): 0.0}
    assert av.mix_demand(y, g, 1.0) == {(5, "a"): 1.0, (6, "b"): 0.0, (5, "c"): 3.0}


def test_wape_parts_inclui_demanda_fora_das_zonas():
    y = {(5, "a"): 4.0}
    err, tot = av.wape_parts({(5, "a"): 3.0}, y, outside=2.0)
    assert (err, tot) == (3.0, 6.0)          # |3−4| + 2 fora; total 4 + 2


def test_oraculo_tem_wape_so_da_demanda_fora():
    y = {(5, "a"): 4.0, (6, "b"): 1.0}
    err, tot = av.wape_parts(av.mix_demand(y, {}, 0.0), y, outside=1.0)
    assert err / tot == pytest.approx(1 / 6)


@pytest.mark.parametrize("target", [0.1, 0.3, 0.5, 0.7])
def test_peso_de_mistura_atinge_o_wape_alvo(target):
    y = {(5, "a"): 4.0, (6, "b"): 2.0, (7, "c"): 3.0}
    g = {(5, "a"): 1.0, (6, "b"): 5.0, (7, "d"): 4.0}
    outside = 1.0
    err_g = sum(abs(g.get(k, 0) - y.get(k, 0)) for k in set(g) | set(y))
    y_tot = sum(y.values()) + outside
    w = av.mixing_weight(target, err_g, y_tot, outside)
    err, tot = av.wape_parts(av.mix_demand(y, g, w), y, outside)
    assert err / tot == pytest.approx(target)


def test_peso_de_mistura_limitado():
    assert av.mixing_weight(5.0, 1.0, 10.0, 0.0) == 1.0     # acima do modelo real: sem extrapolar
    assert av.mixing_weight(0.01, 1.0, 10.0, 5.0) == 0.0    # abaixo do piso da demanda fora das zonas
    assert av.mixing_weight(0.5, 0.0, 10.0, 0.0) == 0.0


def _row(data, cenario, served, pickup, repos=0.0, sim=None, grupo="g", periodo="m", semente=1):
    return {"periodo": periodo, "data": data, "janela": "04-11", "grupo": grupo, "cenario": cenario, "familia": "x",
            "n_requests": 10, "served": served, "pickup_km": pickup, "reposition_km": repos, "empty_km": pickup + repos,
            "empty_km_sim": pickup + repos if sim is None else sim, "overnight_km": 0.0, "wait_sum": 0.0,
            "moves_planned": 1, "moves_executed": 1, "km_planejado": 1.0, "semente": semente}


def test_average_seeds_e_build_pairs():
    rows = [_row("2026-03-16", "a", 10, 20, semente=1), _row("2026-03-16", "a", 12, 22, semente=2),
            _row("2026-03-16", analise.BASE, 9, 18, grupo="base", semente=""),
            _row("2026-03-17", "a", 5, 8), _row("2026-03-17", analise.BASE, 5, 9, grupo="base")]
    days = analise.average_seeds(rows)
    a = [r for r in days if r["cenario"] == "a" and r["data"] == "2026-03-16"][0]
    assert a["served"] == 11 and a["pickup_km"] == 21 and a["sementes"] == 2
    pairs = analise.build_pairs(days, "empty_km", "base")
    pr = pairs[("m", "04-11", "g", "a")]
    assert pr.b["served"].tolist() == [9, 5] and pr.p["served"].tolist() == [11, 5]


def test_build_pairs_usa_o_campo_de_contabilizacao_escolhido():
    rows = [_row("2026-03-16", "a", 10, 20, repos=5, sim=100), _row("2026-03-16", analise.BASE, 10, 20, grupo="base", sim=90)]
    pr = analise.build_pairs(analise.average_seeds(rows), "empty_km_sim", "base")[("m", "04-11", "g", "a")]
    assert pr.p["empty_km"].tolist() == [100] and pr.b["empty_km"].tolist() == [90]


def test_average_seeds_nao_mistura_pares_distintos():
    rows = [dict(_row("2026-03-16", analise.BASE, 10, 20, grupo="base", semente=""), par="B0|rho1"),
            dict(_row("2026-03-16", analise.BASE, 30, 60, grupo="base", semente=""), par="B1|rho1")]
    days = analise.average_seeds(rows)
    assert sorted((r["par"], r["served"]) for r in days) == [("B0|rho1", 10.0), ("B1|rho1", 30.0)]
