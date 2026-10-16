r"""5.4 Busca local em vizinhança grande (LNS) avaliada no simulador sobre pseudodias históricos.

Representação: plano = {motorista: zona de destino} (centróides a até H km). Início: plano do guloso
de valor marginal do artigo (α = 0,2; ρ = 2,5 km; limite 3 km) ou do finalista de 5.1. A cada uma das
E avaliações, um operador gera um vizinho — remover um movimento, trocar destinos entre dois
motoristas movidos, reconstruir k motoristas (ficar ou destino sorteado ∝ λ_z) ou acrescentar um
movimento — e o vizinho substitui o atual só se J (ver `cenarios.py`) diminuir nos pseudodias de busca.
No fim, os pseudodias de aceitação (disjuntos) decidem entre plano inicial, melhor plano e plano vazio.
"""
from __future__ import annotations

from tcc_frota.algoritmos.base import GulosoMarginal, Moves, PlanContext, Planner
from tcc_frota.algoritmos.cenarios import Evaluator, Neighborhood, accept_on_holdout, seeded_rng, split, to_moves, zone_plan

ARTICLE_GREEDY = {"alpha": 0.2, "rho_km": 2.5, "max_km": 3.0}


def start_plan(ctx: PlanContext, start: str, fluxo: dict | None) -> Moves:
    if start == "guloso":
        return GulosoMarginal(**ARTICLE_GREEDY).plan(ctx)
    if start == "fluxo":
        from tcc_frota.algoritmos.fluxo_custo_minimo import FluxoCustoMinimo

        return FluxoCustoMinimo(**fluxo).plan(ctx)
    if start == "vazio":
        return {}
    raise ValueError(start)


class BuscaLocalLNS(Planner):
    family = "busca_local"
    stochastic = True
    needs_scenarios = True

    def __init__(self, inicio: str, avaliacoes: int, k: int, max_km: float, fluxo: dict | None = None):
        super().__init__(max_km)
        self.inicio, self.avaliacoes, self.k, self.fluxo = inicio, avaliacoes, k, fluxo

    @property
    def params(self) -> dict:
        return {"inicio": self.inicio, "avaliacoes": self.avaliacoes, "k": self.k, "max_km": self.max_km, "fluxo": self.fluxo}

    def accept(self, delta: float, step: int, rng) -> bool:
        return delta < -1e-12

    def plan(self, ctx: PlanContext) -> Moves:
        rng = seeded_rng(ctx)
        search, hold = split(ctx.scenarios)
        if not search:
            self.info = {"status": "sem_pseudodias"}
            return {}
        nb = Neighborhood(ctx, self.max_km, rng)
        start = zone_plan(ctx, start_plan(ctx, self.inicio, self.fluxo))
        start = {d: z for d, z in start.items() if (d, z) in nb.km}
        ev = Evaluator(ctx, search, self.max_km)
        cur, f_cur = start, ev.objective(start)
        best, f_best = cur, f_cur
        accepted = 0
        for step in range(self.avaliacoes):
            cand, _ = nb.propose(cur, self.k)
            f = ev.objective(cand)
            if self.accept(f - f_cur, step, rng):
                cur, f_cur = cand, f
                accepted += 1
                if f < f_best - 1e-12:
                    best, f_best = cand, f
        chosen, scores = accept_on_holdout(ctx, hold, self.max_km, {"inicial": start, "melhor": best, "vazio": {}})
        plan = {"inicial": start, "melhor": best, "vazio": {}}[chosen]
        self.info = {"status": "ok", "pseudodias_busca": len(search), "pseudodias_aceitacao": len(hold),
                     "J_busca_inicial": ev.objective(start), "J_busca_melhor": f_best, "J_busca_vazio": ev.objective({}),
                     "aceitos": accepted, "simulacoes": ev.simulations, "escolhido": chosen,
                     "movimentos_inicial": len(start), "movimentos_melhor": len(best), **scores}
        return to_moves(ctx, plan, nb)
