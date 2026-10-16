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
