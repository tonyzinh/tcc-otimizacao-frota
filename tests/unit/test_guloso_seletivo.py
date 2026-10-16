"""Guloso seletivo (C2): permanecer é o padrão, aceitação protegida, salto máximo, determinismo e não vazamento."""
from datetime import date, timedelta

from tcc_frota.algoritmos.base import PlanContext
from tcc_frota.algoritmos.bateria import scenario_days
from tcc_frota.algoritmos.guloso_seletivo import REASONS, GulosoSeletivo, accept, blocks_demand, make_scenarios
from tcc_frota.v2 import forecast as fc
from tcc_frota.v2.sim import SimParams, reta_km

from test_algoritmos_busca import scenarios
from test_v2_policy import instance

SIM = SimParams(4.5, 16.0, 1.3, 180.0)


def ctx(inp, seed=0, scen=(), regime="B"):
    return PlanContext(inp, date(2026, 3, 16), (4, 11), regime, SIM,
                       "fim_do_dia" if regime == "B" else "inicio_turno", scen, seed)


def test_acceptance_rule_requires_mean_above_tau_se_and_rides():
    assert accept([1.0, 1.1, 0.9, 1.0], [10, 10, 10, 10], [10, 10, 10, 10], 2.0) == (True, True)
    assert accept([3.0, -2.0, 2.5, -2.0], [10] * 4, [10] * 4, 1.0)[0] is False   # média > 0 mas dentro do ruído
    assert accept([-0.1, -0.2], [10, 10], [10, 10], 1.0)[0] is False
    assert accept([1.0, 1.0, 1.0], [9, 10, 10], [10, 10, 10], 1.0) == (True, False)


def test_stay_is_the_default_without_scenarios():
    inp = instance(0)
    p = GulosoSeletivo(3.0, 8, 1.0)
    assert p.plan(ctx(inp)) == {}
    assert p.info["permaneceu_sem_candidato"] == len(inp.drivers) and p.info["movido"] == 0


def test_reasons_cover_every_driver_hop_and_determinism():
    for seed in range(4):
        inp = instance(seed)
        sc = scenarios(inp, 6, seed=seed)
        by = {d.did: d for d in inp.drivers}
        p = GulosoSeletivo(3.0, 8, 1.0)
        moves = p.plan(ctx(inp, 5, sc))
        assert moves == GulosoSeletivo(3.0, 8, 1.0).plan(ctx(inp, 5, sc))
        assert sum(p.info[r] for r in REASONS) == len(inp.drivers)
        assert p.info["movido"] == len(moves)
        for did, (lat, lon, km) in moves.items():
            assert km <= 3.0 + 1e-9
            assert abs(km - reta_km(by[did].lat, by[did].lon, lat, lon) * inp.road_factor) < 1e-9


def test_selection_and_validation_use_disjoint_days():
    inp = instance(1)
    sc = scenarios(inp, 6)
    sel, val, disjoint = make_scenarios(ctx(inp, 3, sc), 8)
    assert disjoint and len(sel) == len(val) == 4
    recent = {r.t for s in sc[:3] for r in s.requests}
    old = {r.t for s in sc[3:] for r in s.requests}
    assert all(r.t in recent for g in sel for r in g) and all(r.t in old for g in val for r in g)


def test_blocks_demand_preserves_block_totals():
    inp = instance(2)
    out = blocks_demand(inp)
    for z in inp.zones:
        a = sum(v for (h, zz), v in inp.demand.items() if zz == z and 4 <= h < 7)
        b = sum(v for (h, zz), v in out.demand.items() if zz == z and 4 <= h < 7)
        assert abs(a - b) < 1e-9


class _Hist:
    def __init__(self, days):
        self.history = fc.DemandHistory({}, set(days))


def test_scenario_days_never_include_d_or_d_plus_1():
    target = date(2026, 3, 20)
    days = [target - timedelta(days=k) for k in range(-3, 70)]
    out = scenario_days(_Hist(days), target, fc.ForecastConfig())
    assert out and max(out) < target - timedelta(days=1)
    assert all(d.weekday() == target.weekday() for d in out)
    assert out == sorted(out, reverse=True)


def test_plan_ignores_anything_but_the_context():
    """O planejador só recebe o contexto do corte: outro 'mundo real' de D+1 não muda o plano."""
    inp = instance(3)
    sc = scenarios(inp, 6, seed=1)
    a = GulosoSeletivo(4.0, 8, 1.0).plan(ctx(inp, 2, sc))
    _ = scenarios(inp, 3, seed=99)   # pedidos "reais" diferentes de D+1, nunca entregues ao planejador
    assert a == GulosoSeletivo(4.0, 8, 1.0).plan(ctx(inp, 2, sc))
