from datetime import date, timedelta

import numpy as np
import pytest

from tcc_frota.v3 import fase2
from tcc_frota.v3 import inferencia as inf
from tcc_frota.v3.reamostragem import SCHEMES, indices, scheme_seed

DAYS = tuple(date(2026, 3, 16) + timedelta(days=i) for i in range(16))


def ref_pairs():
    rng = np.random.default_rng(5)
    served_b = rng.poisson(60, 16).astype(float)
    n_req = served_b + rng.poisson(50, 16)
    empty_b = served_b * 2.5 + rng.normal(0, 8, 16)
    mk = lambda s, e: {"n_requests": n_req, "served": s, "pickup_km": e, "reposition_km": np.zeros(16), "empty_km": e, "wait_sum": np.zeros(16)}
    served_p = served_b + rng.normal(0.3, 2, 16)
    empty_p = empty_b + rng.normal(10, 6, 16)
    return inf.Pairs(("m", "04-11", "B", "x"), DAYS, mk(served_b, empty_b), mk(served_p, empty_p))


def test_populacao_nula_tem_efeito_verdadeiro_zero():
    pop = fase2.population(ref_pairs(), 0.0, 0.0)
    assert inf.stat_served_pct(pop) == pytest.approx(0.0, abs=1e-9)
    assert inf.stat_km_vazio_pct(pop) == pytest.approx(0.0, abs=1e-9)


def test_populacao_com_efeito_conhecido():
    ref = ref_pairs()
    assert inf.stat_served_pct(fase2.population(ref, 2.0, 0.0)) == pytest.approx(2.0, rel=0.02)
    assert inf.stat_km_vazio_pct(fase2.population(ref, 0.0, 5.0)) == pytest.approx(-5.0, abs=1e-6)


def test_amostra_tem_forma_e_media_do_extra_correta():
    ref = ref_pairs()
    pop = fase2.population(ref, 2.0, 0.0)
    rng = np.random.default_rng(1)
    idx = np.arange(16)
    mean_served = np.mean([fase2.sample(pop, ref, idx, rng, 2.0).p["served"].sum() for _ in range(300)])
    assert mean_served == pytest.approx(pop.p["served"].sum(), rel=0.01)


def test_decide_detecta_efeito_grande_e_nao_o_nulo():
    ref = ref_pairs()
    boot = {s: indices(s, list(DAYS), 300, scheme_seed("t", s)) for s in SCHEMES}
    big = fase2.population(ref, 8.0, 0.0)
    assert fase2.decide(big, boot)["n"]["reject_widest"] is True
    null = fase2.population(ref, 0.0, 0.0)
    assert fase2.decide(null, boot)["n"]["reject_widest"] is False


def test_curva_nula_tem_falso_positivo_razoavel():
    rows = fase2.curve(ref_pairs(), "t", replicas=120, reps=200, worlds=("iid",))
    null = [r for r in rows if r["efeito"] == "N" and r["delta_n_pct_injetado"] == 0.0][0]
    assert null["rejeita_n_ic_mais_largo"] < 0.25 and null["cobertura_n_ic_mais_largo"] > 0.75
    assert null["verdade_delta_n_pct"] == pytest.approx(0.0, abs=1e-9)
