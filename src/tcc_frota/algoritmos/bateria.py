"""Execução da bateria de algoritmos sob o protocolo único (mesmo mundo, baseline e estatística da v2).

Cada dia avaliado: o mundo D+1 observado (pedidos, sessões, compromissos) é construído uma vez; o
baseline e todos os planos passam pelo mesmo `simulate`, e a assinatura SHA-256 das entradas é
conferida em cada par (RN028). Os planejadores recebem só o `PlanContext` do corte. Algoritmos
estocásticos rodam com cada semente; os determinísticos rodam uma vez (o simulador não tem
aleatoriedade, então as sementes não mudariam nada).
"""
from __future__ import annotations

import importlib
import json
import os
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from tcc_frota.algoritmos.base import Planner, PlanContext, PlannerSpec, Scenario, latlon
from tcc_frota.v2 import experiment as ex
from tcc_frota.v2 import forecast as fc
from tcc_frota.v2.fleet import end_of_day
from tcc_frota.v2.sim import SimParams, simulate

SEEDS = (11, 23, 37, 41, 53)
REFERENCE_RUN = Path("reports/tcc_final/result.json")

# família -> "módulo:Classe" (import tardio para não carregar solvers sem necessidade)
REGISTRY = {
    "nenhum": "tcc_frota.algoritmos.base:SemReposicionamento",
    "guloso_marginal": "tcc_frota.algoritmos.base:GulosoMarginal",
    "proporcional": "tcc_frota.algoritmos.base:Proporcional",
    "regra_limiar": "tcc_frota.algoritmos.base:RegraLimiar",
    "fluxo_custo_minimo": "tcc_frota.algoritmos.fluxo_custo_minimo:FluxoCustoMinimo",
    "hungaro": "tcc_frota.algoritmos.hungaro:HungaroPosicoesEspera",
    "milp": "tcc_frota.algoritmos.milp:MILPBuscaReposicionamento",
    "robusto_cenarios": "tcc_frota.algoritmos.robusto:MILPCenarios",
    "busca_local": "tcc_frota.algoritmos.busca_local:BuscaLocalLNS",
    "recozimento": "tcc_frota.algoritmos.recozimento:RecozimentoSimulado",
    "nsga2": "tcc_frota.algoritmos.nsga2:NSGA2Finalista",
    "pso": "tcc_frota.algoritmos.pso:EnxameParticulas",
}


def build_planner(spec: PlannerSpec) -> Planner:
    module, cls = REGISTRY[spec.family].split(":")
    return getattr(importlib.import_module(module), cls)(**spec.params)


def reference_specs(selection: dict) -> list[PlannerSpec]:
    """Referências obrigatórias, com os parâmetros congelados do artigo (`final-run`)."""
    g, t, p = selection["guloso_marginal"], selection["regra_limiar"], selection["proporcional"]
    out = [PlannerSpec("proporcional", "ref_proporcional", {"max_km": p["max_km"]})]
    for label, alpha in ex.NAMED_ALPHA.items():
        out.append(PlannerSpec("guloso_marginal", f"ref_guloso_a{alpha:g}", {"alpha": alpha, **g}))
    out.append(PlannerSpec("regra_limiar", "ref_regra_limiar", dict(t)))
    return out


@dataclass
class Frozen:
    """O que vem congelado da rodada do artigo: modelo de previsão, seleção das referências e simulador."""

    model: str
    selection: dict
    sims: dict[str, SimParams]


def load_frozen(path: Path = REFERENCE_RUN) -> Frozen:
    res = json.loads(path.read_text(encoding="utf-8"))
    cfg = res["configuracao"]
    return Frozen(cfg["modelo_previsao"], cfg["selecao"], {k: SimParams(**v) for k, v in cfg["simulador"].items()})


def build_study(raw: Path = Path("data/raw")):
    """Silver/Gold locais e `Study` da v2 (mesmo caminho do `final-run`); mede o modelo de viagem."""
    from tcc_frota.v2 import rules
    from tcc_frota.v2.gold import build_gold
    from tcc_frota.v2.raw import prepare_raw
    from tcc_frota.v2.silver import build_silver

    batches = prepare_raw(raw, echo=lambda *a, **k: None)
    silver = build_silver(batches, rules.load_salt())
    study = ex.Study(silver, build_gold(silver))
    for name, period in ex.PERIODS.items():
        m = study.measured_parameters(period.calibration)
        study.trip_model[name] = (m["fator_rua_reta_viagem"], m["velocidade_viagem_kmh"])
    return study


def scenario_days(study, target: date, fconfig: fc.ForecastConfig) -> list[date]:
    """Dias de treino (anteriores a D) do mesmo dia da semana, do mais recente ao mais antigo."""
    train = fc.training_dates(target, study.history, fconfig)
    same = [d for d in train if d.weekday() == target.weekday()]
    return sorted(same, reverse=True)


def build_scenarios(study, period: str, target: date, window: tuple[int, int], fconfig: fc.ForecastConfig) -> tuple[Scenario, ...]:
    out = []
    for d in scenario_days(study, target, fconfig):
        reqs, _ = study.world(period, d, window)
        if reqs:
            out.append(Scenario(d, tuple(reqs)))
    return tuple(out)


def _metrics(res, world_drivers: int) -> dict:
    return {"n_requests": res.n_requests, "served": res.served, "pickup_km": res.pickup_km,
            "reposition_km": res.reposition_km, "empty_km": res.empty_km, "wait_sum": sum(res.wait_s),
            "moves_planned": res.moves_planned, "moves_executed": res.moves_executed,
            "motoristas_mundo": world_drivers, "signature": res.signature}


def evaluate_day(study, period: str, target: date, window_key: str, regime: str, sim: SimParams,
                 specs: list[PlannerSpec], model: str, fconfig: fc.ForecastConfig = fc.ForecastConfig(),
                 seeds: tuple[int, ...] = SEEDS, include_baseline: bool = True) -> list[dict]:
    """Baseline e cada configuração em um dia; uma linha por (configuração, semente efetiva)."""
    window = ex.WINDOWS[window_key]
    move_mode = ex.EXECUTION[regime]
    reqs, drivers = study.world(period, target, window)
    w = (window[0] * 3600.0, window[1] * 3600.0)
    base = simulate(reqs, drivers, sim, w)
    key = {"periodo": period, "data": target.isoformat(), "janela": window_key, "regime": regime}
    rows = []
    if include_baseline:
        rows.append({**key, "familia": "nenhum", "cenario": "sem_reposicionamento", "parametros": "{}",
                     "semente": "", **_metrics(base, len(drivers)), "km_planejado": 0.0, "plan_seconds": 0.0,
                     "info": "{}"})
    if not specs:
        return rows
    inputs, diag = study.plan_inputs(target, window, regime, drivers, sim.road_factor, model, fconfig)
    origins = {d.did: p for d in drivers if (p := study.fleet.last_position(d.did, end_of_day(target)))}
    scenarios: tuple[Scenario, ...] | None = None
    for spec in specs:
        planner = build_planner(spec)
        if getattr(planner, "needs_scenarios", False) and scenarios is None:
            scenarios = build_scenarios(study, period, target, window, fconfig)
        for seed in (seeds if planner.stochastic else seeds[:1]):
            ctx = PlanContext(inputs, target, window, regime, sim, move_mode, scenarios or (), seed)
            start = time.perf_counter()
            moves = planner.plan(ctx)
            elapsed = time.perf_counter() - start
            if any(km > planner.max_km + 1e-6 for _, _, km in moves.values()):
                raise AssertionError(f"{spec.name}: movimento além do salto máximo")
            res = simulate(reqs, drivers, sim, w, latlon(moves), max_move_km=planner.max_km,
                           move_mode=move_mode, move_origins=origins)
            if res.signature != base.signature:
                raise AssertionError("cenários com entradas diferentes (RN028)")
            rows.append({**key, "familia": spec.family, "cenario": spec.name,
                         "parametros": json.dumps(spec.params, sort_keys=True),
                         "semente": seed if planner.stochastic else "", **_metrics(res, len(drivers)),
                         "km_planejado": sum(km for _, _, km in moves.values()), "plan_seconds": elapsed,
                         "info": json.dumps({**planner.info, "frota_plano": diag.get("previstos")}, default=str)})
    return rows


# ------------------------------------------------------------------ execução paralela
_STUDY = None


def _init_worker(raw: str) -> None:
    global _STUDY
    os.environ.setdefault("TCC_REAL_DATA_AUTHORIZED", "YES")
    _STUDY = build_study(Path(raw))


def _evaluator(args):
    if len(args) > 9 and args[9] == "extra":
        from tcc_frota.algoritmos.extras import evaluate_day_ext

        return evaluate_day_ext
    return evaluate_day


def _task(args) -> list[dict]:
    period, day, window_key, regime, sim, specs, model, seeds, include_baseline = args[:9]
    return _evaluator(args)(_STUDY, period, day, window_key, regime, sim, specs, model, seeds=seeds,
                            include_baseline=include_baseline)


def run_tasks(tasks: list[tuple], raw: Path = Path("data/raw"), workers: int = 1, study=None, echo=print) -> list[dict]:
    """Executa tarefas `(período, dia, janela, regime, sim, specs, modelo, sementes, baseline[, "extra"])`."""
    rows: list[dict] = []
    started = time.time()
    if workers <= 1:
        study = study or build_study(raw)
        for i, t in enumerate(tasks, 1):
            rows += _evaluator(t)(study, t[0], t[1], t[2], t[3], t[4], t[5], t[6], seeds=t[7], include_baseline=t[8])
            echo(f"  {i}/{len(tasks)} {t[0]} {t[1]} {t[3]} ({time.time() - started:.0f} s)")
        return rows
    from multiprocessing import get_context

    with get_context("spawn").Pool(workers, initializer=_init_worker, initargs=(str(raw),)) as pool:
        for i, part in enumerate(pool.imap_unordered(_task, tasks), 1):
            rows += part
            if i % max(1, len(tasks) // 10) == 0 or i == len(tasks):
                echo(f"  {i}/{len(tasks)} tarefas ({time.time() - started:.0f} s)")
    rows.sort(key=lambda r: (r["periodo"], r["data"], r["janela"], r["regime"], r["cenario"], str(r["semente"])))
    return rows


def day_list(period: str, stage: str) -> tuple[date, ...]:
    p = ex.PERIODS[period]
    return p.calibration if stage == "calibracao" else p.test
