import random

import pytest

from tcc_frota.v2.sim import SimDriver, SimParams, SimRequest, reta_km, simulate
from tcc_frota.v3.sim import simulate3

PARAMS = SimParams(radius_km=5.0, speed_kmh=30.0, road_factor=1.3, patience_s=300.0)
LAT0, LON0 = -20.30, -40.30
KM_LAT = 1 / 111.19  # graus de latitude por km


def world(seed: int, n_req=40, n_drv=8):
    rng = random.Random(seed)
    reqs = [
        SimRequest(
            i,
            4 * 3600 + rng.uniform(0, 6 * 3600),
            LAT0 + rng.uniform(-3, 3) * KM_LAT,
            LON0 + rng.uniform(-3, 3) * KM_LAT,
            LAT0 + rng.uniform(-6, 6) * KM_LAT,
            LON0 + rng.uniform(-6, 6) * KM_LAT,
            rng.uniform(300, 1200),
            hour=4 + i % 7,
        )
        for i in range(n_req)
    ]
    drivers = []
    for j in range(n_drv):
        start = 4 * 3600 + rng.uniform(0, 3600)
        drivers.append(
            SimDriver(
                f"d{j}",
                ((start, start + rng.uniform(3, 7) * 3600, LAT0 + rng.uniform(-3, 3) * KM_LAT, LON0 + rng.uniform(-3, 3) * KM_LAT),),
            )
        )
    moves = {f"d{j}": (LAT0 + rng.uniform(-3, 3) * KM_LAT, LON0 + rng.uniform(-3, 3) * KM_LAT) for j in range(0, n_drv, 2)}
    origins = {d.did: (LAT0 + rng.uniform(-4, 4) * KM_LAT, LON0 + rng.uniform(-4, 4) * KM_LAT) for d in drivers}
    return reqs, drivers, moves, origins


@pytest.mark.parametrize("seed", range(6))
@pytest.mark.parametrize("mode", ["inicio_turno", "fim_do_dia"])
def test_sem_correcoes_reproduz_a_v1(seed, mode):
    reqs, drivers, moves, origins = world(seed)
    w = (4 * 3600.0, 11 * 3600.0)
    a = simulate(reqs, drivers, PARAMS, w, moves, max_move_km=4.0, move_mode=mode, move_origins=origins)
    b = simulate3(reqs, drivers, PARAMS, w, moves, max_move_km=4.0, move_mode=mode, move_origins=origins)
    for f in (
        "signature",
        "n_requests",
        "served",
        "pickup_km",
        "reposition_km",
        "moves_planned",
        "moves_executed",
        "wait_s",
        "served_ids",
        "move_outcomes",
        "jobs",
    ):
        assert getattr(a, f) == getattr(b, f), f


def test_m1_nao_executa_reposicionamento_que_passa_do_fim_da_sessao():
    # sessão de 5 min; alvo a ~3,9 km por rua (>10 min a 30 km/h)
    d = SimDriver("d0", ((4 * 3600.0, 4 * 3600.0 + 300, LAT0, LON0),))
    target = (LAT0 + 3.0 * KM_LAT, LON0)
    w = (4 * 3600.0, 11 * 3600.0)
    v1 = simulate3([], [d], PARAMS, w, {"d0": target}, max_move_km=5.0, move_mode="inicio_turno")
    fixed = simulate3([], [d], PARAMS, w, {"d0": target}, max_move_km=5.0, move_mode="inicio_turno", fix_m1=True)
    assert v1.moves_executed == 1 and v1.reposition_km > 3.0
    assert fixed.moves_executed == 0 and fixed.reposition_km == 0.0 and fixed.move_outcomes["d0"] == "excede_sessao"


def test_m1_executa_quando_cabe_na_sessao():
    d = SimDriver("d0", ((4 * 3600.0, 8 * 3600.0, LAT0, LON0),))
    out = simulate3(
        [],
        [d],
        PARAMS,
        (4 * 3600.0, 11 * 3600.0),
        {"d0": (LAT0 + 2 * KM_LAT, LON0)},
        max_move_km=5.0,
        move_mode="inicio_turno",
        fix_m1=True,
    )
    assert out.moves_executed == 1


def test_m2_os_dois_bracos_pagam_o_trecho_noturno():
    start = (LAT0, LON0)
    origin = (LAT0 + 1.0 * KM_LAT, LON0)  # última posição de D, ~1 km da posição observada
    target = (LAT0 + 3.0 * KM_LAT, LON0)  # alvo, ~3 km da origem
    d = SimDriver("d0", ((4 * 3600.0 + 600, 9 * 3600.0, *start),))
    w = (4 * 3600.0, 11 * 3600.0)
    common = dict(move_mode="fim_do_dia", move_origins={"d0": origin}, max_move_km=8.0, fix_m2=True)
    base = simulate3([], [d], PARAMS, w, {}, **common)
    moved = simulate3([], [d], PARAMS, w, {"d0": target}, **common)
    natural = reta_km(*origin, *start) * 1.3
    to_target = reta_km(*origin, *target) * 1.3
    assert base.overnight_km == pytest.approx(natural) and base.reposition_km == 0.0
    assert moved.overnight_km == pytest.approx(to_target)
    assert moved.empty_km_sim - base.empty_km_sim == pytest.approx(to_target - natural)
    # sem a correção a v1 cobra o trecho inteiro só do plano
    v1 = simulate3([], [d], PARAMS, w, {"d0": target}, move_mode="fim_do_dia", move_origins={"d0": origin}, max_move_km=8.0)
    assert v1.empty_km_sim == pytest.approx(to_target) and v1.overnight_km == 0.0


def test_m2_motorista_que_ja_trabalhava_fica_fora():
    d = SimDriver("d0", ((3 * 3600.0, 9 * 3600.0, LAT0, LON0),))  # começou > 30 min antes da janela
    out = simulate3(
        [],
        [d],
        PARAMS,
        (4 * 3600.0, 11 * 3600.0),
        {"d0": (LAT0 + 2 * KM_LAT, LON0)},
        move_mode="fim_do_dia",
        move_origins={"d0": (LAT0 + KM_LAT, LON0)},
        max_move_km=8.0,
        fix_m2=True,
    )
    assert out.overnight_km == 0.0 and out.overnight_drivers == 0 and out.move_outcomes["d0"] == "early"


def test_correcoes_nao_mudam_assinatura_nem_atendimento_sem_movimentos():
    reqs, drivers, _, origins = world(3)
    w = (4 * 3600.0, 11 * 3600.0)
    a = simulate3(reqs, drivers, PARAMS, w, {}, move_mode="fim_do_dia", move_origins=origins)
    b = simulate3(reqs, drivers, PARAMS, w, {}, move_mode="fim_do_dia", move_origins=origins, fix_m1=True, fix_m2=True)
    assert a.signature == b.signature and a.served == b.served and a.pickup_km == b.pickup_km


def test_m2_origem_os_dois_bracos_comecam_na_ultima_posicao_de_d():
    start = (LAT0, LON0)
    origin = (LAT0 + 4.0 * KM_LAT, LON0)  # ~4 km do ponto de login
    d = SimDriver("d0", ((4 * 3600.0 + 600, 9 * 3600.0, *start),))
    w = (4 * 3600.0, 11 * 3600.0)
    req = SimRequest(1, 4 * 3600.0 + 900, origin[0], origin[1], origin[0], origin[1] + 0.01, 600.0, hour=4)
    common = dict(move_mode="fim_do_dia", move_origins={"d0": origin}, max_move_km=8.0)
    login = simulate3([req], [d], PARAMS, w, {}, **common)
    orig = simulate3([req], [d], PARAMS, w, {}, start_at_origin=True, **common)
    assert orig.pickup_km == pytest.approx(0.0, abs=1e-6) and login.pickup_km > 4.0
    # com o movimento, o plano paga origem -> alvo e o baseline nada
    target = (LAT0 + 2.0 * KM_LAT, LON0)
    moved = simulate3([req], [d], PARAMS, w, {"d0": target}, start_at_origin=True, **common)
    assert moved.reposition_km == pytest.approx(reta_km(*origin, *target) * 1.3)
    assert orig.reposition_km == 0.0


def test_m2_origem_nao_mexe_em_quem_ja_trabalhava():
    d = SimDriver("d0", ((3 * 3600.0, 9 * 3600.0, LAT0, LON0),))
    out = simulate3(
        [],
        [d],
        PARAMS,
        (4 * 3600.0, 11 * 3600.0),
        {},
        move_mode="fim_do_dia",
        move_origins={"d0": (LAT0 + 5 * KM_LAT, LON0)},
        start_at_origin=True,
    )
    assert out.drift_km == 0.0 and out.pickup_km == 0.0
