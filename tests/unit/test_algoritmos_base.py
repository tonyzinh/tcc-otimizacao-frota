"""Interface Planner: os adaptadores reproduzem exatamente os planejadores existentes."""
from datetime import date

from tcc_frota.algoritmos.base import GulosoMarginal, PlanContext, Proporcional, RegraLimiar, latlon
from tcc_frota.v2.policy import marginal_greedy, proportional, threshold_rule
from tcc_frota.v2.sim import SimParams, reta_km

from test_v2_policy import instance

SIM = SimParams(4.5, 16.0, 1.3, 180.0)


def ctx(inp, seed=0):
    return PlanContext(inp, date(2026, 3, 16), (4, 11), "B", SIM, "fim_do_dia", (), seed)


def test_adapters_match_original_planners():
    for seed in range(15):
        inp = instance(seed)
        for alpha in (0.05, 0.2, 0.5):
            assert latlon(GulosoMarginal(alpha, 2.5, 3.0).plan(ctx(inp))) == \
                marginal_greedy(inp, alpha=alpha, rho_km=2.5, max_km=3.0).moves
        assert latlon(Proporcional(3.0).plan(ctx(inp))) == proportional(inp, max_km=3.0).moves
        assert latlon(RegraLimiar(0.1, 1.5, 3.0).plan(ctx(inp))) == \
            threshold_rule(inp, theta=0.1, rho_km=1.5, max_km=3.0).moves


def test_km_reported_is_road_distance_and_within_hop():
    inp = instance(4)
    by = {d.did: d for d in inp.drivers}
    for planner in (GulosoMarginal(0.05, 2.5, 6.0), Proporcional(6.0), RegraLimiar(0.05, 1.5, 6.0)):
        for did, (lat, lon, km) in planner.plan(ctx(inp)).items():
            assert abs(km - reta_km(by[did].lat, by[did].lon, lat, lon) * inp.road_factor) < 1e-9
            assert km <= planner.max_km + 1e-9


def test_deterministic_planners_ignore_seed():
    inp = instance(7)
    for planner in (GulosoMarginal(0.2, 2.5, 3.0), Proporcional(3.0), RegraLimiar(0.1, 1.5, 3.0)):
        assert not planner.stochastic
        assert planner.plan(ctx(inp, 1)) == planner.plan(ctx(inp, 99))
