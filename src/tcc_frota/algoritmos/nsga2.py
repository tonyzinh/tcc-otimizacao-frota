r"""5.6 NSGA-II multiobjetivo sobre os parâmetros do planejador de fluxo paramétrico.

Decisão (5 genes reais): peso w ∈ [0, 1] do alvo misto (demanda ↔ valor marginal), share ∈ [0,3; 1,6],
salto H ∈ [1,5; 6] km, teto por zona ∈ [1, 6) (⌊·⌋; 6 = sem teto) e km mínimo por movimento ∈ [0; 2].
Objetivos, nos 14 dias de calibração (2–15/03, regime B, 04–11h), no simulador:
f₁ = KM vazio total (busca + reposicionamento) e f₂ = −corridas atendidas.
NSGA-II clássico (Deb et al., 2002): ordenação não dominada, distância de multidão, torneio binário,
cruzamento SBX (η = 15, p = 0,9) e mutação polinomial (η = 20, p = 1/5). População 20 × 15 gerações
= 300 avaliações por semente. A fronteira é a da calibração; o finalista de cada semente é o ponto da
fronteira com menor KM vazio por corrida entre os que têm corridas ≥ 0,99 × baseline. No teste, cada
semente usa o seu finalista (`NSGA2Finalista`) e as métricas do dia são a média das sementes.
Implementação própria (pymoo não está instalado; ver auditoria).
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass

from tcc_frota.algoritmos.base import Moves, PlanContext, Planner, latlon
from tcc_frota.algoritmos.fluxo_custo_minimo import FluxoParametrico

BOUNDS = ((0.0, 1.0), (0.3, 1.6), (1.5, 6.0), (1.0, 6.0 - 1e-9), (0.0, 2.0))
POP, GENERATIONS = 20, 15
ETA_C, ETA_M, P_C = 15.0, 20.0, 0.9


def decode(x: list[float]) -> dict:
    teto = int(x[3])
    return {"peso": round(x[0], 4), "share": round(x[1], 4), "max_km": round(x[2], 4),
            "teto": None if teto >= 6 else teto, "km_min": round(x[4], 4)}


# ------------------------------------------------------------------ NSGA-II genérico (minimização)
def dominates(a: tuple, b: tuple) -> bool:
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def nondominated_sort(objs: list[tuple]) -> list[list[int]]:
    n = len(objs)
    dominated = [[] for _ in range(n)]
    count = [0] * n
    fronts: list[list[int]] = [[]]
    for i in range(n):
        for j in range(n):
            if i != j and dominates(objs[i], objs[j]):
                dominated[i].append(j)
            elif i != j and dominates(objs[j], objs[i]):
                count[i] += 1
        if count[i] == 0:
            fronts[0].append(i)
    k = 0
    while fronts[k]:
        nxt = []
        for i in fronts[k]:
            for j in dominated[i]:
                count[j] -= 1
                if count[j] == 0:
                    nxt.append(j)
        k += 1
        fronts.append(nxt)
    return fronts[:-1]


def crowding(objs: list[tuple], front: list[int]) -> dict[int, float]:
    dist = {i: 0.0 for i in front}
    for m in range(len(objs[front[0]])):
        order = sorted(front, key=lambda i: objs[i][m])
        lo, hi = objs[order[0]][m], objs[order[-1]][m]
        dist[order[0]] = dist[order[-1]] = float("inf")
        if hi - lo <= 0:
            continue
        for a, b, c in zip(order, order[1:], order[2:]):
            dist[b] += (objs[c][m] - objs[a][m]) / (hi - lo)
    return dist


def sbx(p1: list[float], p2: list[float], rng: random.Random) -> tuple[list[float], list[float]]:
    c1, c2 = list(p1), list(p2)
    if rng.random() > P_C:
        return c1, c2
    for k, (lo, hi) in enumerate(BOUNDS):
        if rng.random() > 0.5 or abs(p1[k] - p2[k]) < 1e-12:
            continue
        u = rng.random()
        beta = (2 * u) ** (1 / (ETA_C + 1)) if u <= 0.5 else (1 / (2 * (1 - u))) ** (1 / (ETA_C + 1))
        a = 0.5 * ((1 + beta) * p1[k] + (1 - beta) * p2[k])
        b = 0.5 * ((1 - beta) * p1[k] + (1 + beta) * p2[k])
        c1[k], c2[k] = min(hi, max(lo, a)), min(hi, max(lo, b))
    return c1, c2


def mutate(x: list[float], rng: random.Random) -> list[float]:
    y = list(x)
    for k, (lo, hi) in enumerate(BOUNDS):
        if rng.random() >= 1 / len(BOUNDS):
            continue
        u = rng.random()
        delta = (2 * u) ** (1 / (ETA_M + 1)) - 1 if u < 0.5 else 1 - (2 * (1 - u)) ** (1 / (ETA_M + 1))
        y[k] = min(hi, max(lo, y[k] + delta * (hi - lo)))
    return y


def nsga2(evaluate, rng: random.Random, pop_size: int = POP, generations: int = GENERATIONS):
    """Devolve todas as avaliações [(x, objetivos, extra)] na ordem em que ocorreram."""
    history = []

    def ev(x):
        objs, extra = evaluate(x)
        history.append((x, objs, extra))
        return objs

    pop = [[rng.uniform(lo, hi) for lo, hi in BOUNDS] for _ in range(pop_size)]
    objs = [ev(x) for x in pop]
    for _ in range(generations - 1):
        fronts = nondominated_sort(objs)
        rank = {i: r for r, f in enumerate(fronts) for i in f}
        crowd = {}
        for f in fronts:
            crowd.update(crowding(objs, f))

        def pick():
            a, b = rng.randrange(len(pop)), rng.randrange(len(pop))
            return pop[a] if (rank[a], -crowd[a]) < (rank[b], -crowd[b]) else pop[b]

        children = []
        while len(children) < pop_size:
            c1, c2 = sbx(pick(), pick(), rng)
            children += [mutate(c1, rng), mutate(c2, rng)]
        children = children[:pop_size]
        allx, allo = pop + children, objs + [ev(c) for c in children]
        new, newo = [], []
        for f in nondominated_sort(allo):
            if len(new) + len(f) <= pop_size:
                new += [allx[i] for i in f]
                newo += [allo[i] for i in f]
            else:
                cd = crowding(allo, f)
                for i in sorted(f, key=lambda i: -cd[i])[:pop_size - len(new)]:
                    new.append(allx[i])
                    newo.append(allo[i])
                break
        pop, objs = new, newo
    return history


# ------------------------------------------------------------------ avaliação na calibração
@dataclass
class CalibDay:
    reqs: list
    drivers: list
    inputs: object
    origins: dict
    base_served: int
    base_empty: float
    ctx: PlanContext


def calibration_days(study, frozen, period: str = "mar2026", regime: str = "B", window_key: str = "04-11") -> list[CalibDay]:
    from tcc_frota.v2 import experiment as ex
    from tcc_frota.v2.fleet import end_of_day
    from tcc_frota.v2.sim import simulate

    sim = frozen.sims[period]
    window = ex.WINDOWS[window_key]
    out = []
    for day in ex.PERIODS[period].calibration:
        reqs, drivers = study.world(period, day, window)
        base = simulate(reqs, drivers, sim, (window[0] * 3600.0, window[1] * 3600.0))
        inputs, _ = study.plan_inputs(day, window, regime, drivers, sim.road_factor, frozen.model, ex.fc.ForecastConfig())
        origins = {d.did: p for d in drivers if (p := study.fleet.last_position(d.did, end_of_day(day)))}
        ctx = PlanContext(inputs, day, window, regime, sim, ex.EXECUTION[regime])
        out.append(CalibDay(reqs, drivers, inputs, origins, base.served, base.empty_km, ctx))
    return out


def evaluate_params(days: list[CalibDay], params: dict) -> tuple[tuple[float, float], dict]:
    from tcc_frota.v2.sim import simulate

    planner = FluxoParametrico(**params)
    served = empty = repo = 0.0
    for d in days:
        moves = planner.plan(d.ctx)
        res = simulate(d.reqs, d.drivers, d.ctx.sim, d.ctx.window_s, latlon(moves), max_move_km=planner.max_km,
                       move_mode=d.ctx.move_mode, move_origins=d.origins)
        served += res.served
        empty += res.empty_km
        repo += res.reposition_km
    return (empty, -served), {"corridas": served, "km_vazio": empty, "km_repos": repo}


def search(study, frozen, seed: int) -> dict:
    days = calibration_days(study, frozen)
    base_served = sum(d.base_served for d in days)
    base_empty = sum(d.base_empty for d in days)
    history = nsga2(lambda x: evaluate_params(days, decode(x)), random.Random(seed))
    objs = [h[1] for h in history]
    front = set(nondominated_sort(objs)[0])
    rows = []
    for k, (x, o, extra) in enumerate(history):
        rows.append({"semente": seed, "avaliacao": k, "parametros": json.dumps(decode(x), sort_keys=True),
                     "corridas": extra["corridas"], "km_vazio": extra["km_vazio"], "km_repos": extra["km_repos"],
                     "km_vazio_por_corrida": extra["km_vazio"] / extra["corridas"],
                     "corridas_base": base_served, "km_vazio_base": base_empty,
                     "na_fronteira": k in front, "satisfaz_piso": extra["corridas"] >= 0.99 * base_served - 1e-9})
    feasible = [r for r in rows if r["na_fronteira"] and r["satisfaz_piso"]]
    pool = feasible or [max((r for r in rows if r["na_fronteira"]), key=lambda r: r["corridas"])]
    best = min(pool, key=lambda r: (r["km_vazio_por_corrida"], r["avaliacao"]))
    return {"semente": seed, "finalista": json.loads(best["parametros"]), "linha_finalista": best,
            "regra": "fronteira: menor km vazio/corrida com piso" if feasible else "sem ponto viável na fronteira",
            "avaliacoes": rows}


class NSGA2Finalista(Planner):
    """No teste, a semente s usa o finalista da busca NSGA-II com a semente s."""

    family = "nsga2"
    stochastic = True

    def __init__(self, finalistas: dict):
        self.finalistas = {str(k): v for k, v in finalistas.items()}
        super().__init__(max(v["max_km"] for v in self.finalistas.values()))

    @property
    def params(self) -> dict:
        return {"finalistas": self.finalistas}

    def plan(self, ctx: PlanContext) -> Moves:
        inner = FluxoParametrico(**self.finalistas[str(ctx.seed)])
        self.max_km = inner.max_km          # limite de execução = salto do finalista desta semente
        moves = inner.plan(ctx)
        self.info = {**inner.info, "parametros_semente": self.finalistas[str(ctx.seed)]}
        return moves
