r"""Guloso seletivo por economia líquida de KM (C2), com "permanecer" como decisão padrão.

Estrutura gulosa: pares motorista → zona entram no plano um a um. Muda o critério de aceitação.

**Cenários (sem vazamento).** Só dados até o corte de D: os dias do mesmo dia da semana nos 56 dias
anteriores a D (`PlanContext.scenarios`, do mais recente ao mais antigo, sem o dia D). Metade mais
recente → conjunto de seleção 𝒮; metade mais antiga → validação 𝒱 (dias disjuntos). Cada um gera K/2
cenários: um dia sorteado com reposição + *bootstrap* dos pedidos desse dia, com semente fixa. A frota é
a do regime (escala e posição de partida conhecidas em B; horário previsto), sem compromissos.

**Economia líquida.** Para o plano atual P e o candidato m = (i → z), em cada cenário s, com o mesmo
cenário simulado com e sem m (variáveis aleatórias comuns):

    S_s(m) = [B_s(P) − B_s(P ∪ m)] − [R_s(P ∪ m) − R_s(P)] − λ · [N_s(P) − N_s(P ∪ m)]

B = KM de busca da frota inteira (inclui o efeito de outro veículo assumir corrida mais distante), R = KM
de reposicionamento (reta × fator rua/reta, o d da formulação), N = corridas atendidas, λ = km por
corrida perdida. **Aceitação** (proteção contra o ruído dos cenários): em 𝒮 **e** em 𝒱,

    média(S) > 0,   média(S) > τ · EP(S),   média(N(P ∪ m)) ≥ média(N(P)).

**Busca.** Pré-filtro pelo proxy ΔV do guloso atual (ρ = 2,5 km): pares a até H km com ΔV > 0, no
máximo M por iteração, em ordem decrescente de ΔV. O primeiro par aprovado entra no plano e a iteração
recomeça; o algoritmo para quando nenhum par é aprovado. Cada motorista se move no máximo uma vez.
Motivo por motorista do plano: movido; permaneceu: sem candidato; sem economia; sem ganho de
atendimento; reprovado na validação. O plano D+1 depende só do contexto do corte: alterar os pedidos
reais de D+1 não o altera (teste).

Variantes de previsão espacial (sensibilidade 4.4, só calibração): `blocos3h`, `h3r6`, `deficit`.
"""

from __future__ import annotations

import random
from dataclasses import replace
from math import ceil, sqrt
from statistics import mean, stdev

from tcc_frota.algoritmos.base import Moves, PlanContext, Planner, scenario_drivers
from tcc_frota.v2.policy import PlanInputs, _Coverage, home_zone
from tcc_frota.v2.sim import reta_km, simulate

RHO_KM = 2.5
REASONS = (
    "permaneceu_sem_candidato",
    "permaneceu_sem_economia",
    "permaneceu_sem_ganho_atendimento",
    "permaneceu_reprovado_validacao",
    "movido",
)
BLOCKS = ((4, 7), (7, 10), (10, 11))


# ------------------------------------------------------------------ variantes de previsão (4.4)
def blocks_demand(inp: PlanInputs) -> PlanInputs:
    """(a) Soma a previsão em blocos de 3 h e distribui igualmente entre as horas do bloco."""
    out: dict[tuple[int, str], float] = {}
    for a, b in BLOCKS:
        hours = [h for h in inp.hours if a <= h < b]
        if not hours:
            continue
        tot: dict[str, float] = {}
        for (h, z), v in inp.demand.items():
            if a <= h < b:
                tot[z] = tot.get(z, 0.0) + v
        for z, v in tot.items():
            for h in hours:
                out[(h, z)] = v / len(hours)
    return replace(inp, demand=out)


def r6_inputs(inp: PlanInputs) -> PlanInputs:
    """(b) Zonas H3 r6: demanda somada nas filhas r7 e centróide ponderado pela demanda da janela."""
    import h3

    parent = {z: h3.cell_to_parent(z, 6) for z in inp.zones}
    lam: dict[str, float] = {}
    for (_, z), v in inp.demand.items():
        lam[z] = lam.get(z, 0.0) + v
    acc: dict[str, list[float]] = {}
    for z, (la, lo) in inp.zones.items():
        w = lam.get(z, 0.0) or 1e-6
        a = acc.setdefault(parent[z], [0.0, 0.0, 0.0])
        a[0] += la * w
        a[1] += lo * w
        a[2] += w
    zones = {p: (a[0] / a[2], a[1] / a[2]) for p, a in acc.items()}
    demand: dict[tuple[int, str], float] = {}
    for (h, z), v in inp.demand.items():
        if z in parent:
            demand[(h, parent[z])] = demand.get((h, parent[z]), 0.0) + v
    return replace(inp, zones=zones, demand=demand)


def deficit_inputs(inp: PlanInputs, zones_ok: set[str]) -> PlanInputs:
    """(c) Destinos restritos a zonas com déficit de oferta persistente no histórico (antes do corte)."""
    return replace(inp, demand={k: v for k, v in inp.demand.items() if k[1] in zones_ok})


def accept(s_vals: list[float], n_with: list[float], n_without: list[float], tau: float) -> tuple[bool, bool]:
    """(economia aprovada, atendimento preservado) num conjunto de cenários."""
    mu = mean(s_vals)
    se = stdev(s_vals) / sqrt(len(s_vals)) if len(s_vals) > 1 else 0.0
    return (mu > 0 and mu > tau * se), mean(n_with) >= mean(n_without) - 1e-9


# ------------------------------------------------------------------ cenários
def make_scenarios(ctx: PlanContext, k: int) -> tuple[list[list], list[list], bool]:
    """K/2 cenários de seleção (dias recentes) e K/2 de validação (dias antigos), com sementes fixas."""
    pool = [s for s in ctx.scenarios if s.requests]
    if not pool:
        return [], [], False
    half = ceil(len(pool) / 2)
    sel_days, val_days = (pool[:half], pool[half:]) if len(pool) >= 2 else (pool, pool)
    disjoint = len(pool) >= 2
    out = []
    for tag, days in ((1, sel_days), (2, val_days)):
        group = []
        for j in range(k // 2):
            rng = random.Random(ctx.seed * 1_000_003 + ctx.target.toordinal() * 97 + tag * 7919 + j)
            day = days[rng.randrange(len(days))]
            reqs = day.requests
            idx = sorted(rng.randrange(len(reqs)) for _ in reqs)
            group.append([replace(reqs[i], rid=n) for n, i in enumerate(idx)])
        out.append(group)
    return out[0], out[1], disjoint


class GulosoSeletivo(Planner):
    family = "guloso_seletivo"
    stochastic = True
    needs_scenarios = True

    def __init__(self, max_km: float, k: int, tau: float, lam: float = 0.0, m: int = 30, previsao: str = "padrao"):
        super().__init__(max_km)
        if k < 2 or k % 2:
            raise ValueError("K deve ser par e >= 2")
        if previsao not in ("padrao", "blocos3h", "h3r6", "deficit"):
            raise ValueError(previsao)
        self.k, self.tau, self.lam, self.m, self.previsao = k, tau, lam, m, previsao
        self.needs_deficit_zones = previsao == "deficit"

    @property
    def params(self) -> dict:
        return {"max_km": self.max_km, "k": self.k, "tau": self.tau, "lam": self.lam, "m": self.m, "previsao": self.previsao}

    def _proxy_inputs(self, ctx: PlanContext) -> PlanInputs:
        inp = ctx.inputs
        if self.previsao == "blocos3h":
            return blocks_demand(inp)
        if self.previsao == "h3r6":
            return r6_inputs(inp)
        if self.previsao == "deficit":
            return deficit_inputs(inp, set(ctx.extras.get("zonas_deficit_persistente", ())))
        return inp

    def plan(self, ctx: PlanContext) -> Moves:
        inp = self._proxy_inputs(ctx)
        reasons = {d.did: 0 for d in ctx.inputs.drivers}
        sel, val, disjoint = make_scenarios(ctx, self.k)
        if not sel or not inp.drivers:
            self.info = {"status": "sem_cenarios", **self._count(reasons)}
            return {}
        drivers = scenario_drivers(ctx.inputs)
        origins = {d.did: (d.lat, d.lon) for d in ctx.inputs.drivers}
        cache: dict[tuple, tuple[float, float, float]] = {}
        sims = 0

        def run(plan: dict[str, str], group: int, j: int, reqs: list) -> tuple[float, float, float]:
            nonlocal sims
            key = (frozenset(plan.items()), group, j)
            if key not in cache:
                moves = {did: inp.zones[z] for did, z in plan.items()}
                res = simulate(
                    reqs, drivers, ctx.sim, ctx.window_s, moves, max_move_km=self.max_km, move_mode=ctx.move_mode, move_origins=origins
                )
                cache[key] = (res.served, res.pickup_km, res.reposition_km)
                sims += 1
            return cache[key]

        def check(plan, cand, group, scen) -> tuple[bool, bool]:
            s_vals, n_with, n_without = [], [], []
            for j, reqs in enumerate(scen):
                n0, b0, r0 = run(plan, group, j, reqs)
                n1, b1, r1 = run(cand, group, j, reqs)
                s_vals.append((b0 - b1) - (r1 - r0) - self.lam * (n0 - n1))
                n_with.append(n1)
                n_without.append(n0)
            return accept(s_vals, n_with, n_without, self.tau)

        cov = _Coverage(inp)
        cur = {d.did: home_zone(d.lat, d.lon, inp.zones, RHO_KM) for d in inp.drivers}
        for did, z in cur.items():
            cov.apply(did, z, +1)
        targets = sorted({z for (_, z), v in inp.demand.items() if v > 0 and z in inp.zones})
        km = {(d.did, z): reta_km(d.lat, d.lon, *inp.zones[z]) * inp.road_factor for d in inp.drivers for z in targets}
        plan: dict[str, str] = {}
        iterations = evaluated = 0
        while True:
            iterations += 1
            cands = []
            for d in inp.drivers:
                if d.did in plan:
                    continue
                loss = cov.delta_remove(d.did, cur[d.did])
                for z in targets:
                    if z == cur[d.did] or not (1e-9 < km[(d.did, z)] <= self.max_km + 1e-9):
                        continue
                    gain = cov.delta_add(d.did, z) - loss
                    if gain > 1e-12:
                        cands.append((-gain, d.did, z))
            cands.sort()
            accepted = None
            for _, did, z in cands[: self.m]:
                evaluated += 1
                cand = {**plan, did: z}
                econ, rides = check(plan, cand, 1, sel)
                if not econ:
                    reason = 1
                elif not rides:
                    reason = 2
                else:
                    econ_v, rides_v = check(plan, cand, 2, val)
                    reason = 4 if econ_v and rides_v else 3
                reasons[did] = max(reasons[did], reason)
                if reason == 4:
                    accepted = (did, z)
                    break
            if accepted is None:
                break
            did, z = accepted
            cov.apply(did, cur[did], -1)
            cov.apply(did, z, +1)
            cur[did] = z
            plan[did] = z
        moves = {did: (inp.zones[z][0], inp.zones[z][1], km[(did, z)]) for did, z in plan.items()}
        self.info = {
            "status": "ok",
            "iteracoes": iterations,
            "pares_avaliados": evaluated,
            "simulacoes": sims,
            "cenarios_selecao": len(sel),
            "cenarios_validacao": len(val),
            "dias_disjuntos": disjoint,
            **self._count(reasons),
        }
        return moves

    @staticmethod
    def _count(reasons: dict[str, int]) -> dict[str, int]:
        out = dict.fromkeys(REASONS, 0)
        for v in reasons.values():
            out[REASONS[v]] += 1
        return out
