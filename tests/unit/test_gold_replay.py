"""Experimento D+1 sobre a Gold com linhas artificiais no mesmo formato do cache."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from tcc_frota.distance import CachedDistance, HaversineDistance, haversine_km
from tcc_frota.gold.replay import (
    GoldData, RealExperimentConfig, World, build_world, forecast_zones, materialize,
    predicted_fleet, run_day, training_days,
)
from tcc_frota.models import Commitment, Position, Recommendation, Vehicle
from tcc_frota.optimization.greedy import Plan

TZ = ZoneInfo("America/Sao_Paulo")
UTC = timezone.utc
TARGET = date(2026, 9, 30)  # quarta-feira
CONFIG = RealExperimentConfig(lookback_days=14, min_presence_rate=0.5)
TRAIN = [date(2026, 9, 16), date(2026, 9, 23)]
Z1, Z2 = (-20.30, -40.30), (-20.35, -40.30)


def local(day, hour, minute=0):
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ).astimezone(UTC)


def ride(ride_id, driver, day, hour, minute=0, *, zone=1, tipo="TempoReal", minutes=15, registro=None):
    lat, lon = Z1 if zone == 1 else Z2
    aceite = local(day, hour, minute)
    return {
        "id_corrida": ride_id, "id_motorista_pseud": driver, "tipo_solicitacao": tipo,
        "ts_registro": registro or aceite - timedelta(minutes=1), "ts_aceite": aceite,
        "ts_chegada": aceite + timedelta(minutes=5), "ts_inicio": aceite + timedelta(minutes=6),
        "ts_fim": aceite + timedelta(minutes=6 + minutes), "data_local": day,
        "lat_origem": lat, "lon_origem": lon, "h3_r7_origem": zone,
        "lat_destino": lat, "lon_destino": lon, "h3_r7_destino": zone,
        "km_pickup_reta": 1.0, "km_gps_pickup": 1.3, "min_viagem": float(minutes),
    }


def presence(driver, day, hour=7, zone_r8=11):
    lat, lon = Z1 if zone_r8 == 11 else Z2
    return {"id_motorista_pseud": driver, "data_local": day, "hora_local": hour, "fl_disponivel_na_hora": True,
            "lat_primeira": lat, "lon_primeira": lon, "h3_r8_primeira": zone_r8}


def session(driver, seq, start, end, zone_r8=11, estado="DISPONIVEL"):
    lat, lon = Z1 if zone_r8 == 11 else Z2
    return {"id_motorista_pseud": driver, "seq_sessao": seq, "estado_sessao": estado, "ts_inicio": start,
            "ts_fim": end, "lat_inicio": lat, "lon_inicio": lon, "h3_r8_inicio": zone_r8}


def demand(day, hour, zone, qty):
    return {"data_local": day, "hora_local": hour, "tipo_solicitacao": "TempoReal", "h3_r7": zone,
            "qtd_corridas_atendidas": qty}


def tables(extra_demand=(), extra_presence=(), rides=None, sessions=None):
    train_rides = [ride(f"t{i}{d.day}", "a", d, 8, 10 * i, zone=2) for d in TRAIN for i in range(3)]
    return {
        "tb_dim_zonas_h3": [
            {"h3_r8": 11, "h3_r7": 1, "lat_centro_r7": Z1[0], "lon_centro_r7": Z1[1]},
            {"h3_r8": 22, "h3_r7": 2, "lat_centro_r7": Z2[0], "lon_centro_r7": Z2[1]},
        ],
        "tb_demanda_zona_hora": [demand(d, 8, 2, 3) for d in TRAIN] + list(extra_demand),
        "tb_frota_sessoes": sessions if sessions is not None else [
            session("a", 1, local(TARGET, 6), local(TARGET, 12)),
            session("b", 1, local(TARGET, 6), local(TARGET, 12), zone_r8=22),
        ],
        "tb_frota_motorista_hora": [presence(drv, d, h) for d in TRAIN for drv in ("a", "b") for h in (7, 8, 9)]
        + list(extra_presence),
        "tb_corridas_replay": train_rides + (rides if rides is not None else [ride("r1", "x", TARGET, 8, zone=2)]),
    }


def test_training_days_exclude_cutoff_day_target_and_days_before_data():
    days, fallback = training_days(TARGET, CONFIG)
    assert days == TRAIN and not fallback
    assert max(days) < TARGET - timedelta(days=1)
    assert training_days(TARGET, CONFIG, first_available=date(2026, 9, 20))[0] == [date(2026, 9, 23)]
    with pytest.raises(ValueError):
        training_days(TARGET, CONFIG, first_available=TARGET)


def test_forecast_ignores_cutoff_day_and_target_day():
    base, n = forecast_zones(tables()["tb_demanda_zona_hora"], TARGET, CONFIG)
    leaked = tables(extra_demand=[demand(TARGET, 8, 1, 99), demand(TARGET - timedelta(days=1), 8, 1, 99)])
    assert forecast_zones(leaked["tb_demanda_zona_hora"], TARGET, CONFIG) == (base, n)
    assert base == {"2": 3.0} and n == 2


def test_predicted_fleet_uses_only_history_and_typical_position():
    data = GoldData.from_rows(tables(extra_presence=[presence("c", TARGET), presence("c", TARGET - timedelta(days=1))]))
    fleet = predicted_fleet(data, TARGET, CONFIG)
    assert [v.vehicle_id for v in fleet] == ["a", "b"]
    assert all(v.position.zone == "1" for v in fleet)


def test_world_keeps_in_progress_trip_as_commitment_and_uses_dispatch_time_for_scheduled():
    rides = [
        ride("andamento", "a", TARGET, 6, 50, minutes=30),
        ride("agendada", "b", TARGET, 8, tipo="Agendamento", registro=local(TARGET - timedelta(days=3), 10)),
        ride("fora", "b", TARGET, 11),
    ]
    world = build_world(GoldData.from_rows(tables(rides=rides)), TARGET, CONFIG)
    assert [r.request_id for r in world.requests] == ["agendada"]
    assert world.requests[0].created_at == local(TARGET, 8)
    assert len(world.commitments) == 1 and world.commitments[0].vehicle_id == "a#1"
    assert world.commitments[0].end_position is not None


def _world(commitments=()):
    start = local(TARGET, 7)
    vehicles = [Vehicle("a#1", Position("1", *Z1), start, start + timedelta(hours=5))]
    return World([], vehicles, tuple(commitments), {}, {}), start


def _plan(driver="a"):
    target = Position("2", *Z2)
    return Plan((Recommendation(driver, Position("1", *Z1), target, local(TARGET, 7), 5.0),), 0, 5, 1, 0, 1)


def test_materialize_recomputes_distance_from_actual_position_and_drops_absent():
    world, start = _world()
    applied, status = materialize(_plan(), world, start, 30.0, 12.0)
    assert status == {"aplicada": 1}
    expected = haversine_km(Position("1", *Z1), Position("2", *Z2))
    assert applied[0].distance_km == pytest.approx(expected) and applied[0].start_at == start
    assert materialize(_plan("ausente"), world, start, 30.0, 12.0)[1] == {"motorista_ausente": 1}
    assert materialize(_plan(), world, start, 30.0, 1.0)[1] == {"acima_do_limite": 1}


def test_materialize_waits_for_trip_end_only_within_tolerance():
    _, start = _world()
    end_position = Position("2", -20.33, -40.30)
    busy = Commitment("a#1", start - timedelta(minutes=5), start + timedelta(minutes=20), "corrida", end_position)
    world, _ = _world([busy])
    assert materialize(_plan(), world, start, 30.0, 12.0)[1] == {"motorista_em_corrida": 1}
    applied, status = materialize(_plan(), world, start, 30.0, 12.0, timedelta(minutes=30))
    assert status == {"aplicada": 1}
    assert applied[0].start_at == busy.end and applied[0].origin == end_position


def test_run_day_compares_identical_inputs():
    result = run_day(GoldData.from_rows(tables()), TARGET, CONFIG)
    assert result["comparable_inputs"] is True
    assert result["baseline"]["requests"] == result["proposed"]["requests"] == 1
    assert result["baseline"]["dataset_kind"] == "real_gold_databricks"
    assert result["training_days"] == 2
    assert result["proposed"]["estimated_km_dead_total"] >= result["proposed"]["estimated_reposition_km"]


def test_oracle_is_opt_in_and_labelled_as_cutoff_violation():
    data = GoldData.from_rows(tables())
    assert run_day(data, TARGET, CONFIG)["information_basis"] == "d1_estrito_frota_prevista_no_corte"
    oracle = run_day(data, TARGET, replace(CONFIG, oracle_fleet=True))
    assert oracle["information_basis"] == "diagnostico_oraculo_frota_real_d1_viola_corte"
    assert oracle["comparable_inputs"] is True


def test_config_rejects_tolerance_beyond_horizon():
    with pytest.raises(ValueError):
        replace(CONFIG, execution_tolerance_minutes=180)


def test_cached_distance_matches_base_estimator():
    a, b = Position("1", *Z1), Position("2", *Z2)
    cached = CachedDistance(HaversineDistance())
    assert cached.name == HaversineDistance.name
    assert cached.measure(a, b) == HaversineDistance().measure(a, b) == cached.measure(a, b)
