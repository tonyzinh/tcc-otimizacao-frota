"""Protocolo experimental v2 (Fases 2–6).

Ordem: (1) calibração do simulador por período nos dias de calibração; (2) escolha do modelo de
previsão e dos parâmetros dos algoritmos **somente** nos dias de calibração de março; (3) avaliação
nos dias de teste de março e de setembro com parâmetros congelados; (4) sensibilidades, uma variável
por vez. Tudo o que é testado é guardado nas linhas diárias e reportado.
"""
from __future__ import annotations

import time as _time
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import date, timedelta
from statistics import median

from tcc_frota.v2 import forecast as fc
from tcc_frota.v2.fleet import FleetIndex, build_world, end_of_day, planned_fleet, rides_from_silver
from tcc_frota.v2.gold import Gold
from tcc_frota.v2.policy import PlanInputs, marginal_greedy, proportional, threshold_rule
from tcc_frota.v2.silver import Silver, _km
from tcc_frota.v2.sim import SimParams, reta_km, simulate


def _days(year: int, month: int, first: int, last: int) -> tuple[date, ...]:
    return tuple(date(year, month, d) for d in range(first, last + 1))


@dataclass(frozen=True)
class Period:
    name: str
    calibration: tuple[date, ...]
    test: tuple[date, ...]


PERIODS = {
    "mar2026": Period("mar2026", _days(2026, 3, 2, 15), _days(2026, 3, 16, 31)),
    "set2026": Period("set2026", _days(2026, 9, 2, 15), _days(2026, 9, 16, 30)),
}
WINDOWS = {"04-07": (4, 7), "07-10": (7, 10), "04-11": (4, 11)}
MAIN_WINDOW = "04-11"
MAIN_REGIME = "B"
SELECTION_PERIOD = "mar2026"

# Grades pré-especificadas (registradas em DT014 antes de ver o teste).
RADIUS_GRID = (2.0, 3.0, 4.0, 4.5, 5.0, 6.0, 8.0)
PATIENCE_GRID = (60.0, 90.0, 120.0, 180.0, 240.0)
ALPHA_GRID = (0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 1.0)
NAMED_ALPHA = {"agressiva": 0.05, "intermediaria": 0.2, "conservadora": 0.5}
RHO_GRID = (1.0, 1.5, 2.5)
DMAX_GRID = (3.0, 6.0, 10.0)
THETA_GRID = (0.05, 0.1, 0.2, 0.5)
THRESHOLD_DMAX = (3.0, 6.0)
PROP_DMAX = (3.0, 6.0, 12.0)
FORECAST_MARGIN = 0.05   # modelo mais simples que não perca por mais de 5% no WAPE


class Study:
    def __init__(self, silver: Silver, gold: Gold):
        self.silver = silver
        self.gold = gold
        self.history = fc.DemandHistory.from_gold(gold.demanda_zona_hora)
        self.requests_by_date: dict[date, list[dict]] = defaultdict(list)
        for r in gold.replay_pedidos:
            self.requests_by_date[r["data_local"]].append(r)
        self.fleet = FleetIndex(gold.frota_snapshot, gold.frota_sessoes, rides_from_silver(silver.solicitacoes))
        self.zone_sums: dict[date, dict[str, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0]))
        for r in gold.replay_pedidos:
            if r["h3_r7_origem"]:
                acc = self.zone_sums[r["data_local"]][r["h3_r7_origem"]]
                acc[0] += r["lat_origem"]
                acc[1] += r["lon_origem"]
                acc[2] += 1
        self.driver_hours: dict[tuple[date, int], float] = defaultdict(float)
        for row in gold.frota_motorista_hora:
            self.driver_hours[(row["data_local"], row["hora_local"])] += row["min_trabalhando"] / 60
        self._worlds: dict[tuple, tuple] = {}
        self.trip_model: dict[str, tuple[float, float]] = {}

    # ---------- calibração observada ----------
    def observed(self, dates: tuple[date, ...], window: tuple[int, int]) -> dict[str, float]:
        reqs = [r for d in dates for r in self.requests_by_date.get(d, []) if window[0] <= r["hora_local"] < window[1]]
        accepted = [r for r in reqs if r["fl_aceito"]]
        search = [r["s_registro_ate_chegada"] for r in reqs if r["grupo_desfecho"] == "atendida" and r["s_registro_ate_chegada"]]
        return {"pedidos": len(reqs), "taxa_aceite": len(accepted) / max(1, len(reqs)),
                "busca_mediana_s": median(search) if search else float("nan")}

    def measured_parameters(self, dates: tuple[date, ...]) -> dict[str, float]:
        """Fator rua/reta, velocidade de busca e modelo de duração, só com os dias dados."""
        wanted = set(dates)
        reqs = {r["codigo"]: r for r in self.silver.solicitacoes if r["data_base"] in wanted}
        trip_factor, trip_speed = [], []
        for r in reqs.values():
            if r["status"] == "CorridaEncerrada" and r["dist_percorrida_km"] and r["dur_viagem_s"] and r["lat_destino"] is not None:
                reta = _km(r["lat_origem"], r["lon_origem"], r["lat_destino"], r["lon_destino"])
                if reta >= 0.5:
                    trip_factor.append(r["dist_percorrida_km"] / reta)
                    trip_speed.append(r["dist_percorrida_km"] / (r["dur_viagem_s"] / 3600))
        pick_speed, pick_factor = [], []
        for h in self.silver.historico:
            r = reqs.get(h["codigo"])
            if not r or not h["dist_motorista_m"] or not r["ts_aceite"] or not r["ts_chegada"]:
                continue
            secs = (r["ts_chegada"] - r["ts_aceite"]).total_seconds()
            if secs >= 60 and h["dist_motorista_m"] > 200:
                pick_speed.append(h["dist_motorista_m"] / 1000 / (secs / 3600))
            p = self.fleet.last_position(h["motorista_pseud"], r["ts_aceite"]) if h["motorista_pseud"] else None
            if p:
                reta = _km(p[0], p[1], r["lat_origem"], r["lon_origem"])
                if reta >= 0.5:
                    pick_factor.append(h["dist_motorista_m"] / 1000 / reta)
        return {"fator_rua_reta_busca": median(pick_factor), "n_fator_busca": len(pick_factor),
                "velocidade_busca_kmh": median(pick_speed), "n_velocidade": len(pick_speed),
                "fator_rua_reta_viagem": median(trip_factor), "velocidade_viagem_kmh": median(trip_speed),
                "n_viagem": len(trip_factor)}

    # ---------- mundo e entradas do plano ----------
    def world(self, period: str, target: date, window: tuple[int, int]):
        key = (period, target, window)
        if key not in self._worlds:
            factor, speed = self.trip_model[period]

            def fallback(r):
                return max(120.0, 3600 * reta_km(r["lat_origem"], r["lon_origem"], r["lat_destino"], r["lon_destino"]) * factor / speed)

            self._worlds[key] = build_world(self.fleet, self.requests_by_date.get(target, []), target, window, fallback)
        return self._worlds[key]

    def kappa(self, target: date, window: tuple[int, int]) -> float:
        cut_day = target - timedelta(days=1)
        days = [d for d in self.fleet.dates if cut_day - timedelta(days=28) < d <= cut_day]
        rides = sum(r["fl_aceito"] for d in days for r in self.requests_by_date.get(d, [])
                    if window[0] <= r["hora_local"] < window[1])
        hours = sum(self.driver_hours.get((d, h), 0.0) for d in days for h in range(*window))
        return rides / hours if hours > 0 else 0.5

    def plan_inputs(self, target: date, window: tuple[int, int], regime: str, world_drivers, road_factor: float,
                    model: str, fconfig: fc.ForecastConfig, position_cut_hour: int | None = None) -> tuple[PlanInputs, dict]:
        hours = tuple(range(*window))
        demand = fc.predict(model, target, self.history, range(*window), fconfig)
        train = fc.training_dates(target, self.history, fconfig)
        sums: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
        for d in train:
            for z, (a, b, n) in self.zone_sums.get(d, {}).items():
                acc = sums[z]
                acc[0] += a
                acc[1] += b
                acc[2] += n
        zones = {z: (a / n, b / n) for z, (a, b, n) in sums.items() if n > 0}
        drivers, diag = planned_fleet(regime, self.fleet, target, window, world_drivers,
                                      position_cut_hour=position_cut_hour)
        diag["kappa"] = self.kappa(target, window)
        diag["demanda_prevista"] = sum(demand.values())
        return PlanInputs(tuple(drivers), zones, demand, hours, diag["kappa"], road_factor), diag


def metrics(res, plan=None, plan_seconds: float = 0.0) -> dict:
    return {"n_requests": res.n_requests, "served": res.served, "pickup_km": res.pickup_km,
            "reposition_km": res.reposition_km, "empty_km": res.empty_km, "wait_sum": sum(res.wait_s),
            "wait_median": median(res.wait_s) if res.wait_s else float("nan"),
            "moves_planned": res.moves_planned, "moves_executed": res.moves_executed,
            "planned_gain": plan.expected_gain if plan else 0.0, "planned_km": plan.planned_km if plan else 0.0,
            "plan_seconds": plan_seconds, "signature": res.signature,
            "served_by_hour": dict(res.served_by_hour), "requests_by_hour": dict(res.requests_by_hour),
            "pickup_by_hour": dict(res.pickup_km_by_hour)}


def policy_specs(selection: dict) -> list[tuple[str, str, dict]]:
    """(nome do cenário, algoritmo, parâmetros) avaliados no teste."""
    g = selection["guloso_marginal"]
    specs = [("proporcional", "proporcional", {"max_km": selection["proporcional"]["max_km"]})]
    for alpha in ALPHA_GRID:
        specs.append((f"guloso_marginal_a{alpha:g}", "guloso_marginal",
                      {"alpha": alpha, "rho_km": g["rho_km"], "max_km": g["max_km"]}))
    t = selection["regra_limiar"]
    specs.append(("regra_limiar", "regra_limiar", t))
    return specs


def make_plan(algorithm: str, inputs: PlanInputs, params: dict):
    if algorithm == "proporcional":
        return proportional(inputs, **params)
    if algorithm == "guloso_marginal":
        return marginal_greedy(inputs, **params)
    if algorithm == "regra_limiar":
        return threshold_rule(inputs, **params)
    raise ValueError(algorithm)


EXECUTION = {"A": "inicio_turno", "B": "fim_do_dia", "C": "fim_do_dia"}


def run_day(study: Study, period: str, target: date, window_key: str, regime: str, sim: SimParams,
            specs: list[tuple[str, str, dict]], model: str, fconfig: fc.ForecastConfig, *,
            move_mode: str | None = None, position_cut_hour: int | None = None) -> list[dict]:
    window = WINDOWS[window_key]
    move_mode = move_mode or EXECUTION[regime]
    reqs, drivers = study.world(period, target, window)
    w = (window[0] * 3600.0, window[1] * 3600.0)
    base = simulate(reqs, drivers, sim, w)
    rows = [{"periodo": period, "data": target.isoformat(), "janela": window_key, "regime": regime,
             "cenario": "sem_reposicionamento", "algoritmo": "nenhum", "parametros": {}, **metrics(base)}]
    if not specs:
        return rows
    inputs, diag = study.plan_inputs(target, window, regime, drivers, sim.road_factor, model, fconfig, position_cut_hour)
    origins = {d.did: p for d in drivers if (p := study.fleet.last_position(d.did, end_of_day(target)))}
    diag["execucao"] = move_mode
    for name, algorithm, params in specs:
        start = _time.perf_counter()
        plan = make_plan(algorithm, inputs, params)
        elapsed = _time.perf_counter() - start
        res = simulate(reqs, drivers, sim, w, plan.moves, max_move_km=params["max_km"], move_mode=move_mode,
                       move_origins=origins)
        if res.signature != base.signature:
            raise AssertionError("cenários com entradas diferentes (RN028)")
        rows.append({"periodo": period, "data": target.isoformat(), "janela": window_key, "regime": regime,
                     "cenario": name, "algoritmo": algorithm, "parametros": params, "diag_frota": diag,
                     **metrics(res, plan, elapsed)})
    return rows


def pair_days(rows: list[dict], scenario: str, **filters) -> list[dict]:
    sel = [r for r in rows if all(r[k] == v for k, v in filters.items())]
    base = {r["data"]: r for r in sel if r["cenario"] == "sem_reposicionamento"}
    return [{"b": base[r["data"]], "p": r} for r in sel if r["cenario"] == scenario and r["data"] in base]


def calibrate_simulator(study: Study, period: Period, measured: dict, echo=print) -> tuple[SimParams, list[dict]]:
    """Escolhe raio e paciência que reproduzem aceite e busca mediana observados (janela 04–11)."""
    obs = study.observed(period.calibration, WINDOWS[MAIN_WINDOW])
    grid = []
    for radius in RADIUS_GRID:
        for patience in PATIENCE_GRID:
            sim = SimParams(radius, measured["velocidade_busca_kmh"], measured["fator_rua_reta_busca"], patience)
            served = n = 0
            waits = []
            for day in period.calibration:
                reqs, drivers = study.world(period.name, day, WINDOWS[MAIN_WINDOW])
                res = simulate(reqs, drivers, sim, (WINDOWS[MAIN_WINDOW][0] * 3600.0, WINDOWS[MAIN_WINDOW][1] * 3600.0))
                served += res.served
                n += res.n_requests
                waits += res.wait_s
            rate = served / max(1, n)
            med = median(waits) if waits else float("nan")
            loss = ((rate - obs["taxa_aceite"]) / obs["taxa_aceite"]) ** 2 + ((med - obs["busca_mediana_s"]) / obs["busca_mediana_s"]) ** 2
            grid.append({"periodo": period.name, "raio_km": radius, "paciencia_s": patience,
                         "taxa_atendimento_sim": rate, "taxa_aceite_obs": obs["taxa_aceite"],
                         "tempo_ate_passageiro_mediano_sim_s": med, "busca_mediana_obs_s": obs["busca_mediana_s"],
                         "perda": loss})
    best = min(grid, key=lambda g: (g["perda"], g["raio_km"], g["paciencia_s"]))
    best["escolhido"] = True
    echo(f"[{period.name}] simulador calibrado: raio {best['raio_km']} km, paciência {best['paciencia_s']} s, "
         f"atendimento {best['taxa_atendimento_sim']:.3f} vs {obs['taxa_aceite']:.3f}")
    sim = SimParams(best["raio_km"], measured["velocidade_busca_kmh"], measured["fator_rua_reta_busca"], best["paciencia_s"])
    return sim, grid


def efficiency(days: list[dict]) -> tuple[float, float, float]:
    """(score, Δcorridas, ΔKM vazio) na calibração. Mais corridas por km extra é melhor."""
    dr = sum(d["p"]["served"] - d["b"]["served"] for d in days)
    dk = sum(d["p"]["empty_km"] - d["b"]["empty_km"] for d in days)
    if dk <= 0:
        return (1e9 + dr if dr >= 0 else dr), dr, dk
    return dr / dk, dr, dk
