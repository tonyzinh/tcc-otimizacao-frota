from datetime import date, timedelta

import numpy as np
import pytest

from tcc_frota.v3 import inferencia as inf
from tcc_frota.v3.reamostragem import SCHEMES, indices, scheme_seed

DAYS = [date(2026, 3, 16) + timedelta(days=i) for i in range(16)]


def _pairs(served_b, served_p, empty_b, empty_p):
    n = len(served_b)
    zeros = np.zeros(n)
    mk = lambda s, e: {"n_requests": np.full(n, 100.0), "served": np.array(s, float), "pickup_km": np.array(e, float),
                       "reposition_km": zeros, "empty_km": np.array(e, float), "wait_sum": zeros}
    return inf.Pairs(("m", "04-11", "B", "x"), tuple(DAYS[:n]), mk(served_b, empty_b), mk(served_p, empty_p))


@pytest.mark.parametrize("scheme", SCHEMES)
def test_indices_forma_faixa_e_reprodutibilidade(scheme):
    a = indices(scheme, DAYS, 50, scheme_seed("mar", scheme))
    b = indices(scheme, DAYS, 50, scheme_seed("mar", scheme))
    assert a.shape == (50, 16) and a.min() >= 0 and a.max() <= 15
    assert (a == b).all()


def test_estratificada_preserva_dia_da_semana():
    idx = indices("dow", DAYS, 200, 1)
    weekdays = np.array([d.weekday() for d in DAYS])
    assert (weekdays[idx] == weekdays[None, :]).all()


def test_blocos_geram_corridas_consecutivas():
    idx = indices("circular_b7", DAYS, 200, 1)
    steps = np.diff(idx, axis=1) % 16
    assert (steps == 1).mean() > 0.7  # blocos de 7 preservam vizinhança; iid daria ~1/16


def test_esquema_invalido():
    with pytest.raises(ValueError):
        indices("moving_b3", DAYS, 10, 1)


def test_estatisticas_valores_conhecidos():
    pr = _pairs([10, 10], [11, 11], [20, 20], [22, 22])
    assert inf.stat_served_pct(pr) == pytest.approx(10.0)
    # KM/corrida: base 2,0; plano 2,0 -> 0%
    assert inf.stat_km_vazio_pct(pr) == pytest.approx(0.0)
    assert inf.stat_d_served_day(pr) == pytest.approx(1.0)
    assert inf.stat_d_empty_day(pr) == pytest.approx(2.0)
    # NB(e*) = ΔN − ΔKM/e* = 1 − 2/10
    assert inf.stat_nb(pr, 10) == pytest.approx(0.8)


def test_estatistica_com_indices_igual_ao_ponto_no_resample_identidade():
    pr = _pairs([10, 12, 9], [11, 12, 10], [20, 25, 18], [21, 24, 20])
    ident = np.array([[0, 1, 2]])
    assert inf.stat_km_vazio_pct(pr, ident)[0] == pytest.approx(inf.stat_km_vazio_pct(pr))


def test_divisao_por_zero_vira_nan():
    pr = _pairs([0, 0], [0, 0], [0, 0], [1, 1])
    assert np.isnan(inf.stat_km_vazio_pct(pr))


def test_load_pairs_pareia_baseline(tmp_path):
    f = tmp_path / "d.csv"
    head = "periodo,data,janela,regime,cenario,n_requests,served,pickup_km,reposition_km,empty_km,wait_sum\n"
    f.write_text(head +
                 "m,2026-03-16,04-11,B,sem_reposicionamento,10,5,10,0,10,100\n"
                 "m,2026-03-16,04-11,B,plano,10,6,10,2,12,100\n"
                 "m,2026-03-17,04-11,B,sem_reposicionamento,10,4,8,0,8,100\n"
                 "m,2026-03-17,04-11,B,plano,10,4,8,1,9,100\n", encoding="utf-8")
    out = inf.load_pairs(f)
    pr = out[("m", "04-11", "B", "plano")]
    assert pr.b["served"].tolist() == [5, 4] and pr.p["served"].tolist() == [6, 4]


def test_load_pairs_sem_baseline_falha(tmp_path):
    f = tmp_path / "d.csv"
    f.write_text("periodo,data,janela,regime,cenario,n_requests,served,pickup_km,reposition_km,empty_km,wait_sum\n"
                 "m,2026-03-16,04-11,B,plano,10,6,10,2,12,100\n", encoding="utf-8")
    with pytest.raises(ValueError):
        inf.load_pairs(f)


def test_romano_wolf_domina_o_p_bruto_e_e_monotono():
    rng = np.random.default_rng(0)
    tb = rng.standard_normal((4000, 5))
    t_obs = np.array([4.0, 2.5, 1.0, 0.2, -1.0])
    raw = np.array([(1 + np.sum(tb[:, j] >= t_obs[j])) / 4001 for j in range(5)])
    adj = inf.romano_wolf(t_obs, tb)
    assert (adj >= raw - 1e-12).all()
    order = np.argsort(-t_obs)
    assert (np.diff(adj[order]) >= -1e-12).all()


def test_romano_wolf_uma_hipotese_igual_ao_p_bruto():
    tb = np.random.default_rng(1).standard_normal((3000, 1))
    assert inf.romano_wolf(np.array([1.5]), tb)[0] == pytest.approx((1 + np.sum(tb[:, 0] >= 1.5)) / 3001)


def test_romano_wolf_considera_dependencia():
    rng = np.random.default_rng(2)
    common = rng.standard_normal((4000, 1))
    corr = np.repeat(common, 4, axis=1)                 # testes idênticos
    indep = rng.standard_normal((4000, 4))
    t = np.full(4, 1.8)
    assert inf.romano_wolf(t, corr).max() < inf.romano_wolf(t, indep).max()


def test_holm_confere_com_calculo_manual():
    p = np.array([0.01, 0.04, 0.03])
    # ordenados 0,01*3; 0,03*2; 0,04*1 -> 0,03; 0,06; 0,06 (monotônico)
    assert inf.holm(p) == pytest.approx([0.03, 0.06, 0.06])


def test_fieller_limitado_e_ilimitado():
    rng = np.random.default_rng(3)
    b = 5 + rng.standard_normal(40) * 0.5
    a = 2 * b + rng.standard_normal(40) * 0.2
    lo, hi = inf.fieller(a, b)
    assert lo < 2.0 < hi
    b0 = rng.standard_normal(16)
    b0 -= b0.mean()                                    # média do denominador = 0
    assert inf.fieller(rng.standard_normal(16), b0) is None


def test_mde_e_t_stat():
    assert inf.mde(1.0) == pytest.approx(2.8016, abs=1e-3)
    iv = inf.Interval(-2.0, -3.0, -1.0, 0.5, np.zeros(3))
    assert inf.t_stat(iv, "reducao") == pytest.approx(4.0)
    assert inf.t_stat(iv, "aumento") == pytest.approx(-4.0)
    assert inf.t_stat(iv, "nao_inferior") == pytest.approx(0.0)           # -2 − (−2)
    assert inf.t_stat(inf.Interval(0, 0, 0, 0.0, np.zeros(3)), "reducao") == 0.0
    with pytest.raises(ValueError):
        inf.t_stat(iv, "x")


def test_widest_escolhe_o_intervalo_mais_largo():
    a = inf.Interval(0, -1, 1, 0.5, np.zeros(2))
    b = inf.Interval(0, -3, 2, 1.0, np.zeros(2))
    assert inf.widest({"a": a, "b": b})[0] == "b"


def test_falso_positivo_sob_nulo_nao_explode():
    """Sanidade (não substitui a Fase 2): sem efeito, o IC iid por dia rejeita perto de 5%."""
    rng = np.random.default_rng(4)
    idx = indices("iid", DAYS, 1000, 11)
    rej = 0
    sims = 200
    for _ in range(sims):
        sb = rng.poisson(12, 16)
        eb = sb * 2.5 + rng.normal(0, 3, 16)
        pr = _pairs(sb, rng.poisson(12, 16), eb, rng.poisson(12, 16) * 2.5 + rng.normal(0, 3, 16))
        iv = inf.summarize(inf.stat_km_vazio_pct(pr), inf.stat_km_vazio_pct(pr, idx))
        rej += not (iv.lo <= 0 <= iv.hi)
    assert rej / sims < 0.15
