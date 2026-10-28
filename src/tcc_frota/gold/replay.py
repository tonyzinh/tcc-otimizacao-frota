"""Experimento D+1 com a Gold real: previsão no corte, plano guloso e replay comparável.

Separação de informação (RN020):
* no corte (D às `cutoff_hour`) só entram datas locais anteriores ao dia do corte: demanda por
  zona, presença histórica dos motoristas, posição típica prevista e calibração de velocidade;
* o plano guloso é calculado no corte com frota e posições **previstas**;
* o mundo do replay (pedidos, sessões, posições e corridas em andamento de D+1) é igual nos dois
  cenários e nunca alimenta o plano. No início do horizonte o plano é materializado apenas para
  motoristas previstos que de fato estão livres; os demais contam como não adesão.

Distâncias: Haversine estimado (mesmo estimador nos dois cenários). Não é rodagem observada.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime, time, timedelta
from statistics import median
from time import perf_counter
from zoneinfo import ZoneInfo

from tcc_frota.distance import CachedDistance, HaversineDistance, between_km
from tcc_frota.evaluation.metrics import compare
from tcc_frota.models import Commitment, Position, Recommendation, Request, Vehicle
from tcc_frota.optimization.alternatives import (
    assignment_plan,
    local_search_plan,
    proportional_plan,
    simulated_greedy_plan,
)
from tcc_frota.optimization.greedy import Plan, greedy_plan
from tcc_frota.simulation.engine import SimulationConfig, simulate

Row = Mapping[str, object]


@dataclass(frozen=True)
class RealExperimentConfig:
    plan_hour: int = 7
    horizon_hours: int = 3
    cutoff_hour: int = 20
    lookback_days: int = 56
    min_presence_rate: float = 0.5
    min_coverage: float = 0.0
    max_pickup_km: float = 15.0
    max_reposition_km: float = 12.0
    min_zone_expected: float = 0.05
    execution_tolerance_minutes: float = 30.0
    oracle_fleet: bool = False
    algorithm: str = "guloso"
    timezone: str = "America/Sao_Paulo"

    def __post_init__(self) -> None:
        if not 0 <= self.plan_hour <= 23 or not 1 <= self.horizon_hours <= 24 - self.plan_hour:
            raise ValueError("horizonte inválido")
        if not 0 <= self.cutoff_hour <= 23 or self.lookback_days < 7:
            raise ValueError("corte ou janela histórica inválidos")
        if not 0 < self.min_presence_rate <= 1 or not 0 <= self.min_coverage <= 1:
            raise ValueError("limiares inválidos")
        if not 0 <= self.execution_tolerance_minutes < 60 * self.horizon_hours:
            raise ValueError("tolerância de execução inválida")
        if self.algorithm not in ALGORITHMS:
            raise ValueError(f"algoritmo desconhecido: {self.algorithm}")


@dataclass
class GoldData:
    """Linhas da Gold indexadas por data local."""

    zone_centers: dict[str, tuple[float, float]]
    r8_to_r7: dict[str, str]
    demand: list[Row]
    presence_by_date: dict[date, list[Row]]
    sessions: list[Row]
    rides_by_date: dict[date, list[Row]]
    segments_by_ride: dict[object, Row] = field(default_factory=dict)
    first_date: date | None = None

    @classmethod
    def from_rows(cls, tables: Mapping[str, Iterable[Row]], timezone: str = "America/Sao_Paulo") -> GoldData:
        tz = ZoneInfo(timezone)
        zones = list(tables["tb_dim_zonas_h3"])
        presence: dict[date, list[Row]] = defaultdict(list)
        for row in tables["tb_frota_motorista_hora"]:
            presence[row["data_local"]].append(row)
        rides: dict[date, list[Row]] = defaultdict(list)
        for row in tables["tb_corridas_replay"]:
            started, accepted = row["ts_inicio"].astimezone(tz).date(), row["ts_aceite"].astimezone(tz).date()
            rides[started].append(row)
            if accepted != started:
                rides[accepted].append(row)
        demand = list(tables["tb_demanda_zona_hora"])
        return cls(
            zone_centers={str(z["h3_r7"]): (z["lat_centro_r7"], z["lon_centro_r7"]) for z in zones},
            r8_to_r7={str(z["h3_r8"]): str(z["h3_r7"]) for z in zones},
            demand=demand,
            presence_by_date=dict(presence),
            sessions=list(tables["tb_frota_sessoes"]),
            rides_by_date=dict(rides),
            segments_by_ride={s["id_corrida"]: s for s in tables.get("tb_km_vazio_segmentos", ())},
            first_date=min((row["data_local"] for row in demand), default=None),
        )


def cutoff_for(target: date, config: RealExperimentConfig) -> datetime:
    return datetime.combine(target - timedelta(days=1), time(config.cutoff_hour), tzinfo=ZoneInfo(config.timezone))


def training_days(target: date, config: RealExperimentConfig, first_available: date | None = None) -> tuple[list[date], bool]:
    """Dias completos anteriores ao dia do corte; mesmo dia da semana, com fallback.

    O dia do corte fica fora porque suas horas finais ainda não são conhecidas às `cutoff_hour`.
    Dias anteriores ao início dos dados não entram, para não contarem como demanda zero.
    """
    last = target - timedelta(days=2)
    days = [last - timedelta(days=offset) for offset in range(config.lookback_days)]
    days = [day for day in days if first_available is None or day >= first_available]
    if not days:
        raise ValueError("nenhum dia histórico completo antes do corte")
    same = sorted(day for day in days if day.weekday() == target.weekday())
    return (same, False) if same else (sorted(days), True)


def forecast_zones(
    demand: Iterable[Row], target: date, config: RealExperimentConfig, first_available: date | None = None
) -> tuple[dict[str, float], int]:
    """Média de corridas TempoReal por zona r7 no horizonte, só com dias anteriores ao corte."""
    days, _ = training_days(target, config, first_available)
    allowed = set(days)
    hours = set(range(config.plan_hour, config.plan_hour + config.horizon_hours))
    totals: Counter[str] = Counter()
    for row in demand:
        if row["data_local"] in allowed and row["hora_local"] in hours and row["tipo_solicitacao"] == "TempoReal":
            totals[str(row["h3_r7"])] += int(row["qtd_corridas_atendidas"])
    expected = {zone: count / len(days) for zone, count in totals.items()}
    return {z: v for z, v in sorted(expected.items()) if v >= config.min_zone_expected}, len(days)


def predicted_fleet(data: GoldData, target: date, config: RealExperimentConfig) -> list[Vehicle]:
    """Motoristas com presença histórica frequente na hora do plano e posição típica prevista."""
    days, _ = training_days(target, config, data.first_date)
    present: dict[str, list[str]] = defaultdict(list)
    for day in days:
        for row in data.presence_by_date.get(day, ()):
            if row["hora_local"] == config.plan_hour and row["fl_disponivel_na_hora"] and row["h3_r8_primeira"] is not None:
                zone = data.r8_to_r7.get(str(row["h3_r8_primeira"]))
                if zone in data.zone_centers:
                    present[row["id_motorista_pseud"]].append(zone)
    tz = ZoneInfo(config.timezone)
    start = datetime.combine(target, time(config.plan_hour), tzinfo=tz)
    end = start + timedelta(hours=config.horizon_hours)
    fleet = []
    for driver, zones in sorted(present.items()):
        if len(zones) / len(days) < config.min_presence_rate:
            continue
        zone = sorted(Counter(zones).items(), key=lambda item: (-item[1], item[0]))[0][0]
        lat, lon = data.zone_centers[zone]
        fleet.append(Vehicle(driver, Position(zone, lat, lon), start, end))
    return fleet


def oracle_fleet(world: World, start: datetime, end: datetime) -> list[Vehicle]:
    """Diagnóstico: frota livre e posições reais em D+1. Viola o corte; nunca é resultado D+1."""
    busy = {c.vehicle_id for c in world.commitments if c.start <= start < c.end}
    return [
        Vehicle(v.vehicle_id.split("#")[0], v.position, start, end)
        for v in world.vehicles
        if v.available_from <= start < v.available_until and v.vehicle_id not in busy and v.position is not None
    ]


def calibrate(data: GoldData, target: date, config: RealExperimentConfig) -> dict[str, float]:
    """Velocidade em linha reta, pickup p95 e capacidade, apenas com corridas do treino."""
    days, _ = training_days(target, config, data.first_date)
    tz = ZoneInfo(config.timezone)
    hours = set(range(config.plan_hour, config.plan_hour + config.horizon_hours))
    speeds, pickup_minutes, trips = [], [], 0
    for day in days:
        for ride in data.rides_by_date.get(day, ()):
            if ride["ts_inicio"].astimezone(tz).date() != day:
                continue
            minutes = (ride["ts_chegada"] - ride["ts_aceite"]).total_seconds() / 60
            if minutes > 1 and ride["km_pickup_reta"] and ride["km_pickup_reta"] > 0.2:
                speeds.append(ride["km_pickup_reta"] / (minutes / 60))
            if minutes >= 0:
                pickup_minutes.append(minutes)
            if ride["ts_inicio"].astimezone(tz).hour in hours:
                trips += 1
    driver_hours = sum(
        1 for day in days for row in data.presence_by_date.get(day, ()) if row["hora_local"] in hours and row["fl_disponivel_na_hora"]
    )
    if not speeds or not pickup_minutes or not driver_hours:
        raise ValueError("treino insuficiente para calibrar")
    pickup_minutes.sort()
    return {
        "speed_kmh": round(median(speeds), 3),
        "max_pickup_minutes": round(pickup_minutes[int(0.95 * (len(pickup_minutes) - 1))], 3),
        "trips_per_driver_hour": round(trips / driver_hours, 4),
        "capacity_per_vehicle": round(trips / driver_hours * config.horizon_hours, 4),
    }


@dataclass(frozen=True)
class World:
    requests: list[Request]
    vehicles: list[Vehicle]
    commitments: tuple[Commitment, ...]
    observed: dict[str, float | int]
    excluded: dict[str, int]


def _position(data: GoldData, lat, lon, r7=None, r8=None) -> Position | None:
    if lat is None or lon is None:
        return None
    zone = str(r7) if r7 is not None else data.r8_to_r7.get(str(r8), "sem_zona")
    return Position(zone, float(lat), float(lon))


def build_world(data: GoldData, target: date, config: RealExperimentConfig) -> World:
    """Pedidos, frota e compromissos observados em D+1; idênticos nos dois cenários."""
    tz = ZoneInfo(config.timezone)
    start = datetime.combine(target, time(config.plan_hour), tzinfo=tz)
    end = start + timedelta(hours=config.horizon_hours)
    excluded: Counter[str] = Counter()
    first_position = {
        row["id_motorista_pseud"]: row
        for row in data.presence_by_date.get(target, ())
        if row["hora_local"] == config.plan_hour and row["lat_primeira"] is not None
    }
    vehicles: list[Vehicle] = []
    vehicle_of_driver: dict[str, list[Vehicle]] = defaultdict(list)
    for session in data.sessions:
        if session["estado_sessao"] != "DISPONIVEL" or session["ts_fim"] <= start or session["ts_inicio"] >= end:
            continue
        available_from = max(session["ts_inicio"], start)
        if session["ts_fim"] <= available_from:
            excluded["sessao_sem_duracao"] += 1
            continue
        if session["ts_inicio"] < start and session["id_motorista_pseud"] in first_position:
            row = first_position[session["id_motorista_pseud"]]
            position = _position(data, row["lat_primeira"], row["lon_primeira"], r8=row["h3_r8_primeira"])
        else:
            position = _position(data, session["lat_inicio"], session["lon_inicio"], r8=session["h3_r8_inicio"])
        if position is None:
            excluded["sessao_sem_posicao"] += 1
            continue
        vehicle = Vehicle(f"{session['id_motorista_pseud']}#{session['seq_sessao']}", position, available_from, session["ts_fim"])
        vehicles.append(vehicle)
        vehicle_of_driver[session["id_motorista_pseud"]].append(vehicle)

    requests: list[Request] = []
    commitments: list[Commitment] = []
    observed = {"rides": 0, "km_pickup_reta": 0.0, "km_gps_pickup": 0.0}
    seen: set[object] = set()
    for ride in data.rides_by_date.get(target, ()) + data.rides_by_date.get(target - timedelta(days=1), []):
        if ride["id_corrida"] in seen:
            continue
        seen.add(ride["id_corrida"])
        instant = ride["ts_registro"] if ride["tipo_solicitacao"] == "TempoReal" else ride["ts_aceite"]
        origin = _position(data, ride["lat_origem"], ride["lon_origem"], r7=ride["h3_r7_origem"])
        destination = _position(data, ride["lat_destino"], ride["lon_destino"], r7=ride["h3_r7_destino"])
        if ride["ts_aceite"] < start < ride["ts_fim"]:
            owner = [v for v in vehicle_of_driver.get(ride["id_motorista_pseud"], ()) if v.available_from <= start < v.available_until]
            if owner and destination is not None:
                commitments.append(Commitment(owner[0].vehicle_id, ride["ts_aceite"], ride["ts_fim"], "corrida_em_andamento", destination))
            continue
        if not start <= instant < end:
            continue
        if origin is None or destination is None or not ride["min_viagem"] or ride["min_viagem"] <= 0:
            excluded["corrida_sem_posicao_ou_duracao"] += 1
            continue
        requests.append(Request(str(ride["id_corrida"]), instant, origin, destination, float(ride["min_viagem"])))
        observed["rides"] += 1
        observed["km_pickup_reta"] += float(ride["km_pickup_reta"] or 0.0)
        observed["km_gps_pickup"] += float(ride["km_gps_pickup"] or 0.0)
    return World(
        sorted(requests, key=lambda r: (r.created_at, r.request_id)),
        vehicles,
        tuple(sorted(commitments, key=lambda c: (c.vehicle_id, c.start))),
        observed,
        dict(excluded),
    )


def materialize(
    plan: Plan, world: World, start: datetime, speed_kmh: float, max_reposition_km: float, tolerance: timedelta = timedelta(0)
) -> tuple[tuple[Recommendation, ...], dict[str, int]]:
    """Aplica o plano do corte aos motoristas previstos que ficam livres até `start + tolerance`.

    O instante e a origem vêm do mundo observado, igual nos dois cenários: início da sessão ou fim
    da corrida em andamento. A decisão (quem vai para qual zona) continua sendo a do corte.
    """
    estimator = HaversineDistance()
    status: Counter[str] = Counter()
    by_driver = defaultdict(list)
    for vehicle in world.vehicles:
        by_driver[vehicle.vehicle_id.split("#")[0]].append(vehicle)
    limit = start + tolerance
    applied = []
    for rec in plan.recommendations:
        candidates = sorted(
            (v for v in by_driver.get(rec.vehicle_id, ()) if v.available_from <= limit and v.available_until > start),
            key=lambda v: v.available_from,
        )
        if not candidates:
            status["motorista_ausente"] += 1
            continue
        vehicle = candidates[0]
        at, origin = max(start, vehicle.available_from), vehicle.position
        busy = [c for c in world.commitments if c.vehicle_id == vehicle.vehicle_id and c.start <= at < c.end]
        if busy:
            at, origin = busy[0].end, busy[0].end_position
            if at > limit or origin is None:
                status["motorista_em_corrida"] += 1
                continue
        distance = between_km(estimator, origin, rec.destination)
        finish = at + timedelta(hours=distance / speed_kmh)
        if distance < 1e-9:
            status["ja_na_zona"] += 1
        elif distance > max_reposition_km:
            status["acima_do_limite"] += 1
        elif finish > vehicle.available_until or any(
            c.vehicle_id == vehicle.vehicle_id and c.start < finish and c.end > at for c in world.commitments
        ):
            status["conflito_disponibilidade"] += 1
        else:
            applied.append(Recommendation(vehicle.vehicle_id, origin, rec.destination, at, distance))
            status["aplicada"] += 1
    return tuple(applied), dict(status)


def run_day(data: GoldData, target: date, config: RealExperimentConfig, *, details: bool = False) -> dict[str, object]:
    tz = ZoneInfo(config.timezone)
    start = datetime.combine(target, time(config.plan_hour), tzinfo=tz)
    end = start + timedelta(hours=config.horizon_hours)
    calibration = calibrate(data, target, config)
    expected, n_days = forecast_zones(data.demand, target, config, data.first_date)
    zones = {z: Position(z, *data.zone_centers[z]) for z in expected if z in data.zone_centers}
    expected = {z: v for z, v in expected.items() if z in zones}
    world = build_world(data, target, config)
    fleet = oracle_fleet(world, start, end) if config.oracle_fleet else predicted_fleet(data, target, config)
    estimator = CachedDistance(HaversineDistance())
    sim = SimulationConfig(start, end, speed_kmh=calibration["speed_kmh"], max_pickup_minutes=calibration["max_pickup_minutes"])
    clock = perf_counter()
    plan = build_plan(data, target, config, fleet, zones, expected, start, calibration, sim, estimator) if fleet and zones else None
    plan_seconds = perf_counter() - clock
    recommendations, execution = (
        materialize(
            plan, world, start, calibration["speed_kmh"], config.max_reposition_km, timedelta(minutes=config.execution_tolerance_minutes)
        )
        if plan
        else ((), {})
    )
    baseline = simulate(
        "baseline_sem_reposicionamento", world.requests, world.vehicles, sim, commitments=world.commitments, estimator=estimator
    )
    proposed = simulate(
        f"preventivo_{config.algorithm}_d1",
        world.requests,
        world.vehicles,
        sim,
        commitments=world.commitments,
        recommendations=recommendations,
        estimator=estimator,
    )
    result = compare(baseline, proposed, minimum_coverage=None, dataset_kind="real_gold_databricks")
    observed_coverage = len(world.requests)
    result.update(
        {
            "target_date": target.isoformat(),
            "information_basis": (
                "diagnostico_oraculo_frota_real_d1_viola_corte" if config.oracle_fleet else "d1_estrito_frota_prevista_no_corte"
            ),
            "cutoff": cutoff_for(target, config).isoformat(),
            "window": [start.isoformat(), end.isoformat()],
            "training_days": n_days,
            "calibration": calibration,
            "forecast": {
                "zones": len(expected),
                "expected_rides": round(sum(expected.values()), 3),
                "observed_rides_in_window": observed_coverage,
            },
            "algorithm": config.algorithm,
            "plan": {
                "predicted_fleet": len(fleet),
                "recommendations": len(plan.recommendations) if plan else 0,
                "plan_seconds": round(plan_seconds, 3),
                "planned_reposition_km": round(plan.reposition_km, 6) if plan else 0.0,
                "projected_pickup_saving_km": (round(plan.baseline_projected_pickup_km - plan.projected_pickup_km, 6) if plan else 0.0),
                "execution": execution,
            },
            "world": {
                "requests": len(world.requests),
                "vehicles": len(world.vehicles),
                "commitments_in_progress": len(world.commitments),
                "excluded": world.excluded,
            },
            "historical_reference": {
                "label": "politica real observada; metodo e despacho diferentes, nao comparavel como reducao",
                **{k: round(v, 6) if isinstance(v, float) else v for k, v in world.observed.items()},
            },
        }
    )
    if details:
        result["details"] = day_details(
            expected, zones, fleet, plan, recommendations, world, start, set(baseline.served_ids), set(proposed.served_ids)
        )
    return result


def _point(position: Position) -> dict[str, object]:
    return {"zona": position.zone, "lat": round(position.lat, 4), "lon": round(position.lon, 4)}


def day_details(expected, zones, fleet, plan, applied, world, start, served_base, served_prop) -> dict[str, object]:
    """Detalhe de um dia para visualização local; sem IDs de corrida, só pseudônimos de motorista."""
    return {
        "zonas": [{**_point(zones[z]), "demanda_prevista": round(v, 3)} for z, v in sorted(expected.items())],
        "frota_prevista": [{"motorista": v.vehicle_id, **_point(v.position)} for v in fleet],
        "planejadas": [
            {"motorista": r.vehicle_id, "de": _point(r.origin), "para": _point(r.destination), "km": round(r.distance_km, 3)}
            for r in (plan.recommendations if plan else ())
        ],
        "executadas": [
            {
                "motorista": r.vehicle_id.split("#")[0],
                "de": _point(r.origin),
                "para": _point(r.destination),
                "km": round(r.distance_km, 3),
                "inicio": r.start_at.isoformat(),
            }
            for r in applied
        ],
        "frota_real_inicio": [
            {"motorista": v.vehicle_id.split("#")[0], **_point(v.position), "disponivel_desde": v.available_from.isoformat()}
            for v in world.vehicles
            if v.available_from <= start
        ],
        "pedidos": [
            {
                "instante": r.created_at.isoformat(),
                **_point(r.origin),
                "atendido_baseline": r.request_id in served_base,
                "atendido_preventivo": r.request_id in served_prop,
            }
            for r in world.requests
        ],
    }


ALGORITHMS = ("guloso", "proporcional", "atribuicao_otima", "busca_local", "guloso_simulado")


def training_scenarios(data: GoldData, target: date, config: RealExperimentConfig, k: int = 4) -> list[list[Request]]:
    """Pedidos reais dos k dias de treino mais recentes, deslocados para a data alvo."""
    days, _ = training_days(target, config, data.first_date)
    scenarios = []
    for day in days[-k:]:
        shift = target - day
        scenarios.append([replace(r, created_at=r.created_at + shift) for r in build_world(data, day, config).requests])
    return scenarios


def build_plan(
    data: GoldData,
    target: date,
    config: RealExperimentConfig,
    fleet: list[Vehicle],
    zones: dict[str, Position],
    expected: dict[str, float],
    start: datetime,
    calibration: Mapping[str, float],
    sim: SimulationConfig,
    estimator,
) -> Plan:
    """Despacha para o algoritmo escolhido; todos usam só informação do corte."""
    capacity = max(calibration["capacity_per_vehicle"], 1e-6)
    common = dict(max_reposition_km=config.max_reposition_km, estimator=estimator)
    if config.algorithm in {"guloso", "busca_local"}:
        plan = greedy_plan(
            fleet,
            zones,
            expected,
            start,
            capacity_per_vehicle=capacity,
            min_coverage=config.min_coverage,
            max_pickup_km=config.max_pickup_km,
            speed_kmh=calibration["speed_kmh"],
            **common,
        )
        if config.algorithm == "guloso":
            return plan
        return local_search_plan(
            fleet,
            zones,
            expected,
            start,
            initial=plan,
            capacity_per_vehicle=capacity,
            max_pickup_km=config.max_pickup_km,
            min_coverage=config.min_coverage,
            seed=target.toordinal(),
            **common,
        )
    if config.algorithm == "proporcional":
        return proportional_plan(fleet, zones, expected, start, capacity_per_vehicle=capacity, max_pickup_km=config.max_pickup_km, **common)
    if config.algorithm == "atribuicao_otima":
        return assignment_plan(fleet, zones, expected, start, capacity_per_vehicle=capacity, max_pickup_km=config.max_pickup_km, **common)
    return simulated_greedy_plan(
        fleet, zones, expected, start, scenarios=training_scenarios(data, target, config), sim_config=sim, **common
    )


_WORKER_DATA: GoldData | None = None


def _init_worker(cache_dir: str) -> None:
    global _WORKER_DATA
    from tcc_frota.gold.export import TABLES, read_table

    _WORKER_DATA = GoldData.from_rows({name: read_table(cache_dir, name) for name in TABLES})


def _run_day_worker(target: date, config: RealExperimentConfig, details: bool = False) -> dict[str, object]:
    assert _WORKER_DATA is not None
    return run_day(_WORKER_DATA, target, config, details=details)


def run_period(
    cache_dir: str, first: date, last: date, config: RealExperimentConfig, *, workers: int = 1, details: bool = False
) -> dict[str, object]:
    """Executa cada dia de forma independente (corte próprio) e agrega só dias comparáveis."""
    if last < first or workers < 1:
        raise ValueError("período ou paralelismo inválido")
    targets = [first + timedelta(days=offset) for offset in range((last - first).days + 1)]
    if workers == 1:
        _init_worker(str(cache_dir))
        days = [_run_day_worker(day, config, details) for day in targets]
    else:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(workers, initializer=_init_worker, initargs=(str(cache_dir),)) as pool:
            days = list(pool.map(_run_day_worker, targets, [config] * len(targets), [details] * len(targets)))
    comparable = [d for d in days if d["coverage_constraint_met"]]
    base = sum(d["baseline"]["estimated_km_dead_total"] for d in comparable)
    prop = sum(d["proposed"]["estimated_km_dead_total"] for d in comparable)
    totals = {
        "days": len(days),
        "days_coverage_not_worse": len(comparable),
        "baseline_km_dead_estimated": round(base, 3),
        "proposed_km_dead_estimated": round(prop, 3),
        "proposed_reposition_km": round(sum(d["proposed"]["estimated_reposition_km"] for d in comparable), 3),
        "reduction_percent_days_coverage_not_worse": round(100 * (base - prop) / base, 4) if base > 0 else None,
        "baseline_served": sum(d["baseline"]["served"] for d in days),
        "proposed_served": sum(d["proposed"]["served"] for d in days),
        "requests": sum(d["baseline"]["requests"] for d in days),
    }
    run_id = hashlib.sha256(json.dumps([asdict(config), first.isoformat(), last.isoformat()], sort_keys=True).encode()).hexdigest()[:12]
    return {"run_id": run_id, "config": asdict(config), "period": [first.isoformat(), last.isoformat()], "totals": totals, "days": days}
