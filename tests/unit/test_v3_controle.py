import math

from tcc_frota.v2.sim import reta_km
from tcc_frota.v3 import controle as c
from tcc_frota.v3.fase2_controle import EXPERIMENTS
from tcc_frota.algoritmos.base import PlannerSpec


def test_zona_quente_a_hop_km_do_centro():
    z = c.zone_centers()
    for lado in c.SIDES:
        assert math.isclose(reta_km(*z["C"], *z[lado]), c.HOP_KM, rel_tol=0.01)


def test_pedidos_deterministicos_e_na_janela():
    a, b = c.make_requests(3, "E"), c.make_requests(3, "E")
    assert [(r.t, r.lat, r.lon) for r in a] == [(r.t, r.lat, r.lon) for r in b]
    assert all(c.WINDOW[0] * 3600 <= r.t < c.WINDOW[1] * 3600 for r in a)
    assert [r.rid for r in a] == list(range(len(a)))
    assert sum(r.zone == "E" for r in a) > sum(r.zone == "C" for r in a)


def test_lado_quente_fixo_e_sorteado():
    assert {c.hot_side(i, "fixa") for i in range(20)} == {"E"}
    assert len({c.hot_side(i, "sorteada") for i in range(40)}) == 4


def test_frota_comeca_na_zona_fria_e_origens_coincidem():
    drivers, origins = c.make_fleet(0)
    assert len(drivers) == c.N_DRIVERS
    for d in drivers:
        assert origins[d.did] == d.sessions[0][2:]
        assert reta_km(*origins[d.did], *c.zone_centers()["C"]) <= 0.2 + 1e-6


def test_fora_do_raio_baseline_nao_atende_a_zona_quente_e_plano_atende():
    spec = PlannerSpec("proporcional", "proporcional", {"max_km": 3.0})
    rows = c.run_day(0, "fora_do_raio", [spec], mode="fixa", forecast="verdadeira")
    base = next(r for r in rows if r["cenario"] == "sem_reposicionamento")
    plan = next(r for r in rows if r["cenario"] == "proporcional")
    assert base["served"] < 0.3 * base["n_requests"]
    assert plan["served"] > 0.8 * plan["n_requests"] and plan["moves_executed"] > 0
    assert plan["n_requests"] == base["n_requests"]


def test_movimento_para_onde_ja_esta_nao_muda_nada():
    spec = PlannerSpec("proporcional", "proporcional", {"max_km": 3.0})
    rows = c.run_day(1, "alcancavel", [spec], mode="fixa", forecast="verdadeira", null_move=True)
    base = next(r for r in rows if r["cenario"] == "sem_reposicionamento")
    plan = next(r for r in rows if r["cenario"] == "proporcional")
    assert plan["moves_executed"] == 0
    for k in ("served", "pickup_km", "empty_km", "wait_sum"):
        assert plan[k] == base[k]


def test_experimentos_declarados():
    assert EXPERIMENTS["positivo"] == ("fixa", "verdadeira", False)
    assert EXPERIMENTS["negativo_previsao_sem_informacao"][1] == "uniforme"


def test_linhas_de_controles_nulos_tem_mesmas_colunas():
    from tcc_frota.v3 import fase2_controle as f
    rows = f.nulls([PlannerSpec("proporcional", "proporcional", {"max_km": 3.0})])
    assert len({tuple(r) for r in rows}) == 1
    assert all(r["max_abs_delta_atendidas"] == 0 and r["max_abs_delta_km_vazio"] == 0 for r in rows)
