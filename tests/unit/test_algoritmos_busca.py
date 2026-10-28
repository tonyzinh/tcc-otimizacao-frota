"""5.4/5.5/5.8: busca no simulador sobre pseudodias históricos."""

import random
from datetime import date

from test_v2_policy import instance

from tcc_frota.algoritmos.base import PlanContext, Scenario
from tcc_frota.algoritmos.busca_local import BuscaLocalLNS
from tcc_frota.algoritmos.cenarios import Evaluator, split
from tcc_frota.v2.sim import SimParams, SimRequest, reta_km

SIM = SimParams(4.5, 16.0, 1.3, 180.0)


def scenarios(inp, n=4, per_day=30, seed=0):
    rng = random.Random(seed)
    zones = sorted(inp.zones.items())
    out = []
    for k in range(n):
        reqs = []
        for i in range(per_day):
            z, (lat, lon) = rng.choice(zones)
            reqs.append(
                SimRequest(
                    i,
                    rng.uniform(4 * 3600, 8 * 3600),
                    lat + rng.uniform(-0.005, 0.005),
                    lon + rng.uniform(-0.005, 0.005),
                    lat,
                    lon + 0.02,
                    900.0,
                    None,
                    False,
                    5,
                    z,
                )
            )
        out.append(Scenario(date(2026, 3, 9 - k), tuple(sorted(reqs, key=lambda r: r.t))))
    return tuple(out)


def ctx(inp, seed=0, scen=(), regime="B"):
    return PlanContext(inp, date(2026, 3, 16), (4, 11), regime, SIM, "fim_do_dia" if regime == "B" else "inicio_turno", scen, seed)


def test_split_is_disjoint_and_recent_first():
    inp = instance(0)
    sc = scenarios(inp, 5)
    search, hold = split(sc)
    assert len(search) == 3 and len(hold) == 2
    assert not {s.day for s in search} & {s.day for s in hold}
    assert split(sc[:1]) == (sc[:1], sc[:1])


def test_lns_deterministic_by_seed_and_respects_hop():
    inp = instance(3)
    sc = scenarios(inp)
    by = {d.did: d for d in inp.drivers}
    p = BuscaLocalLNS("guloso", 40, 2, 4.0)
    a = p.plan(ctx(inp, 1, sc))
    assert a == BuscaLocalLNS("guloso", 40, 2, 4.0).plan(ctx(inp, 1, sc))
    for did, (lat, lon, km) in a.items():
        assert km <= 4.0 + 1e-9
        assert abs(km - reta_km(by[did].lat, by[did].lon, lat, lon) * inp.road_factor) < 1e-9
    assert p.info["escolhido"] in ("inicial", "melhor", "vazio")
    assert p.info["J_busca_melhor"] <= p.info["J_busca_inicial"] + 1e-12


def test_lns_without_scenarios_does_not_move():
    inp = instance(1)
    assert BuscaLocalLNS("guloso", 20, 2, 4.0).plan(ctx(inp, 0, ())) == {}


def test_holdout_choice_is_the_minimum_on_holdout():
    inp = instance(5)
    sc = scenarios(inp, 4, seed=2)
    p = BuscaLocalLNS("guloso", 30, 4, 4.0)
    p.plan(ctx(inp, 2, sc))
    scores = {k.removeprefix("J_aceitacao_"): v for k, v in p.info.items() if k.startswith("J_aceitacao_")}
    assert scores[p.info["escolhido"]] == min(scores.values())


def test_evaluator_floor_penalty():
    inp = instance(2)
    ev = Evaluator(ctx(inp, 0, scenarios(inp)), scenarios(inp), 4.0)
    served, empty, repo = ev.base
    assert repo == 0 and ev.objective({}) == empty / served


def test_annealing_and_pso_deterministic_and_within_hop():
    from tcc_frota.algoritmos.pso import EnxameParticulas
    from tcc_frota.algoritmos.recozimento import RecozimentoSimulado

    inp = instance(6)
    sc = scenarios(inp, seed=3)
    for make in (lambda: RecozimentoSimulado(0.02, 0.98, 40, 4.0), lambda: EnxameParticulas(0.8, 0.5, 5, 4, 4.0)):
        p = make()
        a = p.plan(ctx(inp, 4, sc))
        assert a == make().plan(ctx(inp, 4, sc))
        assert all(km <= 4.0 + 1e-9 for *_, km in a.values())
        assert p.info["escolhido"] in ("inicial", "melhor", "vazio")


def test_annealing_accepts_worse_only_with_positive_temperature():
    import random as _r

    from tcc_frota.algoritmos.recozimento import RecozimentoSimulado

    hot, cold = RecozimentoSimulado(1e3, 1.0, 1, 4.0), RecozimentoSimulado(0.0, 0.5, 1, 4.0)
    rng = _r.Random(0)
    assert hot.accept(0.01, 0, rng) and not cold.accept(0.01, 0, rng) and cold.accept(-0.01, 0, rng)
