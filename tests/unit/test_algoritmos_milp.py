"""5.3 MILP: piso de atendimento no modelo, salto máximo, determinismo e consistência do objetivo."""
from datetime import date

import pytest

from tcc_frota.algoritmos.base import PlanContext
from tcc_frota.algoritmos.milp import MILPBuscaReposicionamento
from tcc_frota.v2.sim import SimParams, reta_km

from test_v2_policy import instance

SIM = SimParams(4.5, 16.0, 1.3, 180.0)


def ctx(inp, seed=0):
    return PlanContext(inp, date(2026, 3, 16), (4, 11), "B", SIM, "fim_do_dia", (), seed)


@pytest.mark.parametrize("cap,beta", [(1.0, 1.0), (1.5, 0.99), (3.0, 1.0)])
def test_floor_hop_and_objective(cap, beta):
    for seed in range(4):
        inp = instance(seed)
        by = {d.did: d for d in inp.drivers}
        p = MILPBuscaReposicionamento(cap, beta, 0.0, 4.0)
        moves = p.plan(ctx(inp))
        assert p.info["status"] == 0
        assert p.info["atendidas_modelo"][0] >= beta * p.info["S0"][0] - 1e-5
        for did, (lat, lon, km) in moves.items():
            assert km <= 4.0 + 1e-9
            assert abs(km - reta_km(by[did].lat, by[did].lon, lat, lon) * inp.road_factor) < 1e-9
        assert p.info["objetivo"] == pytest.approx(p.info["busca_modelo_km"][0] + p.info["repos_modelo_km"], rel=1e-6, abs=1e-6)
        assert moves == MILPBuscaReposicionamento(cap, beta, 0.0, 4.0).plan(ctx(inp, 7))


def test_relaxed_floor_never_costs_more_and_big_move_penalty_stops_moves():
    for seed in range(4):
        inp = instance(seed)
        strict = MILPBuscaReposicionamento(1.5, 1.0, 0.0, 4.0)
        loose = MILPBuscaReposicionamento(1.5, 0.99, 0.0, 4.0)
        strict.plan(ctx(inp))
        loose.plan(ctx(inp))
        assert loose.info["objetivo"] <= strict.info["objetivo"] + 1e-6
        assert MILPBuscaReposicionamento(1.5, 0.0, 1e4, 4.0).plan(ctx(inp)) == {}


def test_scenario_milp_floor_per_scenario_and_cvar_not_below_mean():
    from tcc_frota.algoritmos.milp import solve
    from tcc_frota.algoritmos.alvos import window_demand
    inp = instance(2)
    lam = window_demand(inp)
    lams = [{z: v * f for z, v in lam.items()} for f in (0.6, 1.0, 1.5)]
    _, mean_info = solve(inp, lams, cap=1.5, beta=1.0, mu=0.0, hop=4.0, radius=4.5, objective="esperado")
    _, cvar_info = solve(inp, lams, cap=1.5, beta=1.0, mu=0.0, hop=4.0, radius=4.5, objective="cvar")
    for info in (mean_info, cvar_info):
        assert info["status"] == 0
        for served, s0 in zip(info["atendidas_modelo"], info["S0"]):
            assert served >= s0 - 1e-5
    assert cvar_info["objetivo"] >= mean_info["objetivo"] - 1e-6   # CVaR de custo >= média


def test_robust_planner_is_seeded_and_uses_only_scenarios():
    from tcc_frota.algoritmos.robusto import MILPCenarios
    from test_algoritmos_busca import scenarios
    inp = instance(3)
    sc = scenarios(inp, 4)
    c = PlanContext(inp, date(2026, 3, 16), (4, 11), "B", SIM, "fim_do_dia", sc, 3)
    p = MILPCenarios(5, "esperado", 1.5, 0.99, 0.0, 4.0)
    assert p.plan(c) == MILPCenarios(5, "esperado", 1.5, 0.99, 0.0, 4.0).plan(c)
    assert p.info["cenarios"] == 5 and p.info["status"] == 0
    assert MILPCenarios(5, "cvar", 1.5, 0.99, 0.0, 4.0).plan(ctx(inp)) == {}   # sem pseudodias: não move
