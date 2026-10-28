"""Avaliação de planos no simulador sobre pseudodias históricos (sem informação de D+1).

Usado por LNS (5.4), recozimento (5.5) e PSO (5.8). Cada pseudodia = pedidos reais de um dia de treino
anterior a D, do mesmo dia da semana, na mesma janela; frota = motoristas que o regime enxerga no corte
(posição e horário previstos), sem compromissos (desconhecidos no corte). O plano é executado como no
regime (fim de D ou início do turno) e com o mesmo salto máximo.

Objetivo (menor é melhor), com piso de atendimento δ = 1% contra o plano vazio nos mesmos pseudodias:

    J(plano) = KM vazio / corridas + 10 · max(0, 0,99 · corridas_0 − corridas) / corridas_0

Os pseudodias são divididos em busca (metade mais recente) e aceitação (os demais); o planejador
escolhe, na aceitação, entre plano inicial, melhor plano da busca e plano vazio.
"""

from __future__ import annotations

import random
from math import ceil

from tcc_frota.algoritmos.alvos import window_demand
from tcc_frota.algoritmos.base import Moves, PlanContext, Scenario, scenario_drivers
from tcc_frota.v2.sim import reta_km, simulate

FLOOR = 0.99
PENALTY = 10.0
OPS = (("remover", 0.3), ("trocar", 0.2), ("reconstruir", 0.3), ("acrescentar", 0.2))

ZonePlan = dict[str, str]  # motorista -> zona de destino


def split(scenarios: tuple[Scenario, ...]) -> tuple[tuple[Scenario, ...], tuple[Scenario, ...]]:
    if len(scenarios) < 2:
        return scenarios, scenarios
    k = ceil(len(scenarios) / 2)
    return scenarios[:k], scenarios[k:]


class Evaluator:
    def __init__(self, ctx: PlanContext, scenarios: tuple[Scenario, ...], hop: float):
        self.ctx, self.scenarios, self.hop = ctx, scenarios, hop
        self.drivers = scenario_drivers(ctx.inputs)
        self.origins = {d.did: (d.lat, d.lon) for d in ctx.inputs.drivers}
        self.cache: dict[frozenset, tuple[float, float, float]] = {}
        self.simulations = 0
        self.base = self.totals({})

    def totals(self, plan: ZonePlan) -> tuple[float, float, float]:
        """(corridas, KM vazio, KM de reposicionamento) somados nos pseudodias."""
        key = frozenset(plan.items())
        if key not in self.cache:
            zones = self.ctx.inputs.zones
            moves = {did: zones[z] for did, z in plan.items()}
            served = empty = repo = 0.0
            for s in self.scenarios:
                res = simulate(
                    list(s.requests),
                    self.drivers,
                    self.ctx.sim,
                    self.ctx.window_s,
                    moves,
                    max_move_km=self.hop,
                    move_mode=self.ctx.move_mode,
                    move_origins=self.origins,
                )
                served += res.served
                empty += res.empty_km
                repo += res.reposition_km
                self.simulations += 1
            self.cache[key] = (served, empty, repo)
        return self.cache[key]

    def objective(self, plan: ZonePlan) -> float:
        served, empty, _ = self.totals(plan)
        served0 = self.base[0]
        if served <= 0:
            return float("inf") if served0 > 0 else 0.0
        short = max(0.0, FLOOR * served0 - served) / served0 if served0 > 0 else 0.0
        return empty / served + PENALTY * short


class Neighborhood:
    """Destinos candidatos (centróides a até H, com demanda prevista) e operadores de vizinhança."""

    def __init__(self, ctx: PlanContext, hop: float, rng: random.Random, max_candidates: int | None = None):
        inp = ctx.inputs
        lam = window_demand(inp)
        self.rng = rng
        self.cands: dict[str, list[tuple[str, float]]] = {}
        self.km: dict[tuple[str, str], float] = {}
        for d in inp.drivers:
            opts = []
            for z, v in lam.items():
                km = reta_km(d.lat, d.lon, *inp.zones[z]) * inp.road_factor
                if 1e-9 < km <= hop + 1e-9:
                    opts.append((z, v))
                    self.km[(d.did, z)] = km
            opts.sort(key=lambda o: (-o[1], o[0]))
            if max_candidates:
                opts = opts[:max_candidates]
            if opts:
                self.cands[d.did] = opts
        self.movable = sorted(self.cands)

    def random_zone(self, did: str) -> str:
        opts = self.cands[did]
        total = sum(v for _, v in opts)
        x = self.rng.random() * total
        for z, v in opts:
            x -= v
            if x <= 0:
                return z
        return opts[-1][0]

    def propose(self, plan: ZonePlan, k: int) -> tuple[ZonePlan, str]:
        if not self.movable:
            return dict(plan), "nenhum"
        r = self.rng.random()
        acc = 0.0
        op = OPS[-1][0]
        for name, p in OPS:
            acc += p
            if r < acc:
                op = name
                break
        moved = sorted(plan)
        new = dict(plan)
        if op in ("remover", "trocar") and not moved:
            op = "acrescentar"
        if op == "remover":
            new.pop(self.rng.choice(moved))
        elif op == "trocar":
            if len(moved) < 2:
                new.pop(moved[0])
            else:
                a, b = self.rng.sample(moved, 2)
                za, zb = plan[a], plan[b]
                if (a, zb) in self.km and (b, za) in self.km and za != zb:
                    new[a], new[b] = zb, za
                else:
                    new.pop(self.rng.choice((a, b)))
        elif op == "reconstruir":
            for did in self.rng.sample(self.movable, min(k, len(self.movable))):
                if self.rng.random() < 0.5:
                    new.pop(did, None)
                else:
                    new[did] = self.random_zone(did)
        else:
            free = [d for d in self.movable if d not in plan]
            if free:
                did = self.rng.choice(free)
                new[did] = self.random_zone(did)
        return new, op


def zone_plan(ctx: PlanContext, moves: Moves) -> ZonePlan:
    """Converte movimentos para centróides em plano por zona (descarta destinos que não são centróides)."""
    rev = {c: z for z, c in ctx.inputs.zones.items()}
    return {did: rev[(lat, lon)] for did, (lat, lon, _) in moves.items() if (lat, lon) in rev}


def to_moves(ctx: PlanContext, plan: ZonePlan, nb: Neighborhood) -> Moves:
    zones = ctx.inputs.zones
    return {did: (zones[z][0], zones[z][1], nb.km[(did, z)]) for did, z in plan.items() if (did, z) in nb.km}


def accept_on_holdout(ctx: PlanContext, hold: tuple[Scenario, ...], hop: float, candidates: dict[str, ZonePlan]) -> tuple[str, dict]:
    """Escolhe, nos pseudodias de aceitação, o melhor entre os candidatos (empate: menos movimentos)."""
    ev = Evaluator(ctx, hold, hop)
    scores = {name: ev.objective(p) for name, p in candidates.items()}
    best = min(scores, key=lambda n: (scores[n], len(candidates[n]), n))
    return best, {f"J_aceitacao_{n}": v for n, v in scores.items()}


def seeded_rng(ctx: PlanContext, salt: int = 0) -> random.Random:
    return random.Random(ctx.seed * 1_000_003 + ctx.target.toordinal() * 31 + salt)
