"""Corte D+1 sem vazamento (RN020) na previsão de demanda e na frota planejada (Fases 2 e 3)."""
from datetime import date, datetime, time, timedelta

import pytest

from tcc_frota.v2 import forecast as fc
from tcc_frota.v2.fleet import FleetIndex, planned_fleet, rides_from_silver
from tcc_frota.v2.rules import TZ
from tcc_frota.v2.sim import SimDriver

TARGET = date(2026, 3, 18)          # D+1; corte às 20h de 17/03


def history(extra=None):
    counts = {}
    for k in range(1, 70):
        day = TARGET - timedelta(days=k)
        for h in (5, 6):
            counts[(day, h, "z1")] = 3 + (day.weekday() == TARGET.weekday())
            counts[(day, h, "z2")] = 1
    counts.update(extra or {})
    return fc.DemandHistory(counts, {d for d, _, _ in counts})


@pytest.mark.parametrize("model", fc.MODELS)
def test_cut_day_and_target_day_do_not_change_forecast(model):
    base = fc.predict(model, TARGET, history(), range(5, 7))
    leaked = fc.predict(model, TARGET, history({(TARGET, 5, "z1"): 999, (TARGET - timedelta(days=1), 5, "z1"): 999,
                                                (TARGET, 6, "z9"): 50}), range(5, 7))
    assert base and base == leaked


def test_training_dates_exclude_cut_day_and_carnaval():
    h = history()
    days = fc.training_dates(TARGET, h, fc.ForecastConfig())
    assert max(days) == TARGET - timedelta(days=2) and TARGET - timedelta(days=1) not in days
    assert not set(days) & set(fc.CARNAVAL_2026)
    assert len(days) == 56 - len(fc.CARNAVAL_2026)   # [D−56, D) sem os 5 dias de Carnaval


def test_models_recover_weekday_level():
    mean = fc.predict("media_dia_semana", TARGET, history(), range(5, 7))
    naive = fc.predict("naive_sazonal", TARGET, history(), range(5, 7))
    pois = fc.predict("poisson", TARGET, history(), range(5, 7))
    assert mean[(5, "z1")] == pytest.approx(4.0) and naive[(5, "z1")] == 4.0
    assert pois[(5, "z1")] == pytest.approx(4.0, rel=0.15)


def _snap(did, when, lat):
    return {"motorista_pseud": did, "ts_snapshot": when, "estado": 1, "fl_coordenada_valida": True,
            "lat": lat, "lon": -40.3}


def test_planned_fleet_never_uses_positions_from_target_day():
    """A: só posições até 20h de D. B: até o fim de D. Nenhum regime além de C usa D+1."""
    cut = datetime.combine(TARGET - timedelta(days=1), time(20), TZ)
    snaps = [_snap("a", cut - timedelta(hours=2), -20.30),
             _snap("a", datetime.combine(TARGET - timedelta(days=7), time(5), TZ), -20.31),
             _snap("a", datetime.combine(TARGET - timedelta(days=14), time(5), TZ), -20.31)]
    late_d = snaps + [_snap("a", cut + timedelta(hours=1), -20.40)]
    with_target = late_d + [_snap("a", datetime.combine(TARGET, time(5), TZ), -20.95)]
    world = [SimDriver("a", ((5 * 3600.0, 9 * 3600.0, -20.95, -40.3),))]
    a1, _ = planned_fleet("A", FleetIndex(snaps, [], []), TARGET, (4, 11), world)
    a2, _ = planned_fleet("A", FleetIndex(with_target, [], []), TARGET, (4, 11), world)
    assert [x.lat for x in a1] == [x.lat for x in a2] == [-20.30]
    b1, _ = planned_fleet("B", FleetIndex(late_d, [], []), TARGET, (4, 11), world)
    b2, _ = planned_fleet("B", FleetIndex(with_target, [], []), TARGET, (4, 11), world)
    assert [x.lat for x in b1] == [x.lat for x in b2] == [-20.40]
    b20, _ = planned_fleet("B", FleetIndex(with_target, [], []), TARGET, (4, 11), world, position_cut_hour=20)
    assert [x.lat for x in b20] == [-20.30]
    oracle, _ = planned_fleet("C", FleetIndex(with_target, [], []), TARGET, (4, 11), world)
    assert oracle[0].lat == -20.95


def test_scheduled_ride_occupies_driver_only_near_the_ride():
    t = datetime(2026, 3, 18, 7, tzinfo=TZ)
    row = {"fl_aceito": True, "motorista_pseud": "a", "ts_aceite": t - timedelta(days=2), "fl_imediata": False,
           "ts_chegada": t, "ts_inicio": t + timedelta(minutes=2), "ts_agendamento": t, "ts_fim": t + timedelta(minutes=30),
           "ts_status_final": None, "status": "CorridaEncerrada", "lat_destino_real": -20.2, "lon_destino_real": -40.2,
           "lat_destino": -20.2, "lon_destino": -40.2, "lat_origem": -20.3, "lon_origem": -40.3, "codigo": 1}
    ride = rides_from_silver([row])[0]
    assert ride["start"] == t - timedelta(minutes=15) and ride["end"] == t + timedelta(minutes=30)
    immediate = rides_from_silver([dict(row, fl_imediata=True, ts_aceite=t - timedelta(minutes=8))])[0]
    assert immediate["start"] == t - timedelta(minutes=8)
