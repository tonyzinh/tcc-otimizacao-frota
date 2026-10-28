import pytest

from tcc_frota.v2.sim import SimDriver, SimParams, SimRequest, reta_km
from tcc_frota.v3.deriva import (Cruise, GoTo, LocalCruise, Observed, ObservedTracks, ReactiveConfig, ReturnHome,
                                 observed_pieces)
from tcc_frota.v3.sim import simulate3

PARAMS = SimParams(radius_km=5.0, speed_kmh=30.0, road_factor=1.0, patience_s=300.0)
LAT0, LON0 = -20.30, -40.30
K = 1 / 111.19
W = (4 * 3600.0, 11 * 3600.0)


def req(rid, t, dlat_km=0.0):
    return SimRequest(rid, t, LAT0 + dlat_km * K, LON0, LAT0 + 1 * K, LON0, 600.0, hour=int(t // 3600))


def driver(did="d0", start=4 * 3600.0, end=10 * 3600.0, lat=LAT0, lon=LON0):
    return SimDriver(did, ((start, end, lat, lon),))


def test_goto_para_no_destino_e_conta_km():
    g = GoTo(0.0, (LAT0, LON0), (LAT0 + 3 * K, LON0), 30.0, 1.0)
    (lat, _), km = g.position(360.0)           # 6 min a 30 km/h = 3 km
    assert km == pytest.approx(3.0, rel=1e-3) and lat == pytest.approx(LAT0 + 3 * K, rel=1e-6)
    assert g.position(10_000.0)[1] == pytest.approx(3.0, rel=1e-3)         # não passa do destino
    assert g.position(0.0)[1] == 0.0


def test_cruise_fica_na_vizinhanca_e_km_cresce():
    c = Cruise(0.0, (LAT0, LON0), (LAT0, LON0), 2.0, 30.0, 1.0, seed=7)
    last = -1.0
    for t in range(0, 7200, 300):
        (lat, lon), km = c.position(float(t))
        assert abs(lat - LAT0) <= 1.0 * K * 1.05 and km >= last - 1e-9
        last = km
    assert last > 5.0


def test_cruise_reprodutivel():
    a = Cruise(0.0, (LAT0, LON0), (LAT0, LON0), 2.0, 30.0, 1.0, seed=7).position(3000.0)
    b = Cruise(0.0, (LAT0, LON0), (LAT0, LON0), 2.0, 30.0, 1.0, seed=7).position(3000.0)
    assert a == b


def test_observed_integra_pecas_parciais():
    o = Observed(100.0, (LAT0, LON0), ((0.0, 600.0, 6 * K, 0.0, 6.0),))     # 6 km em 600 s
    (lat, _), km = o.position(400.0)                                       # 300 s dentro da peça = metade
    assert km == pytest.approx(300 / 600 * 6.0)
    assert lat == pytest.approx(LAT0 + 3 * K, rel=1e-6)


def test_observed_pieces_descarta_gaps_e_saltos():
    snaps = [(0.0, LAT0, LON0, 1), (600.0, LAT0 + K, LON0, 1),              # ok: 1 km em 10 min
             (1200.0, LAT0 + K, LON0, 3),                                    # em corrida: descarta
             (1800.0, LAT0 + K, LON0, 1), (3000.0, LAT0 + 2 * K, LON0, 1),  # gap de 20 min: descarta
             (3600.0, LAT0 + 2 * K, LON0, 1), (3660.0, LAT0 + 12 * K, LON0, 1)]   # 10 km em 1 min: salto de GPS
    pieces = observed_pieces(snaps, 1.3)
    assert len(pieces) == 2
    assert pieces[0][4] == pytest.approx(reta_km(LAT0, LON0, LAT0 + K, LON0) * 1.3)
    assert all(p[1] - p[0] <= 720 for p in pieces)


def test_retorno_a_origem_paga_km_e_volta():
    # corrida termina a 1 km de casa; sem pedidos depois, o veículo volta e o KM entra em drift_km
    res = simulate3([req(1, 4 * 3600.0 + 60)], [driver()], PARAMS, W, drift=ReturnHome())
    assert res.served == 1 and res.drift_km == pytest.approx(reta_km(LAT0 + K, LON0, LAT0, LON0), rel=1e-2)
    base = simulate3([req(1, 4 * 3600.0 + 60)], [driver()], PARAMS, W)
    assert base.drift_km == 0.0 and base.pickup_km == res.pickup_km


def test_veiculo_em_deriva_continua_despachavel_na_posicao_interpolada():
    # B1: livre a 1 km de casa voltando; pedido na casa chega depois: busca menor que a do baseline parado
    r2 = req(2, 4 * 3600.0 + 60 + 600 + 400)          # depois da corrida (pedido 1) e do retorno parcial
    stay = simulate3([req(1, 4 * 3600.0 + 60), r2], [driver()], PARAMS, W)
    back = simulate3([req(1, 4 * 3600.0 + 60), r2], [driver()], PARAMS, W, drift=ReturnHome())
    assert back.served == stay.served == 2
    assert back.pickup_km < stay.pickup_km


def test_irrecuperavel_nunca_e_atendido_e_nao_muda_o_resto():
    reqs = [req(1, 4 * 3600.0 + 60), req(2, 4 * 3600.0 + 7200)]
    ok = simulate3(reqs, [driver()], PARAMS, W)
    cut = simulate3(reqs, [driver()], PARAMS, W, unrecoverable=frozenset({2}))
    assert ok.served == 2 and cut.served == 1 and 2 not in cut.served_ids and cut.n_requests == 2


def test_reativo_envia_livre_para_pedido_perdido():
    # d0 ocupado em corrida longa e d1 livre a 2 km de um ponto onde pedidos são perdidos
    far = SimDriver("d1", ((4 * 3600.0, 10 * 3600.0, LAT0 + 10 * K, LON0),))     # fora do raio (5 km): não atende
    lost = [req(i, 4 * 3600.0 + 100 + i, dlat_km=0.0) for i in range(1, 3)]
    no = simulate3(lost, [far], PARAMS, W)
    yes = simulate3(lost, [far], PARAMS, W, reactive=ReactiveConfig(tick_s=300, lookback_s=900, max_km=12.0))
    assert no.served == 0 and no.drift_km == 0.0
    assert yes.drift_km > 0.0           # foi mandado em direção à origem dos pedidos perdidos


def test_politicas_sem_efeito_quando_desligadas():
    reqs = [req(1, 4 * 3600.0 + 60), req(2, 4 * 3600.0 + 5000)]
    a = simulate3(reqs, [driver()], PARAMS, W)
    b = simulate3(reqs, [driver()], PARAMS, W, drift=None, unrecoverable=frozenset(), reactive=None)
    assert (a.served, a.pickup_km, a.drift_km) == (b.served, b.pickup_km, b.drift_km)
    assert LocalCruise().name.startswith("B3") and ObservedTracks({}).name.startswith("B2")
