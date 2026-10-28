r"""5.8 Enxame de partículas (PSO) sobre representação discreta (índice de destino por motorista).

Cada motorista i tem até 8 destinos candidatos (centróides a até H km, os de maior demanda prevista).
Posição contínua x_i ∈ [0, K_i + 1); decodificação ⌊x_i⌋ = 0 → fica, k → k-ésimo candidato.
Atualização padrão: v ← w·v + c₁·u₁·(pbest − x) + c₂·u₂·(gbest − x), |v| ≤ (K_i + 1)/2, x recortado.
Partículas iniciais: plano vazio, plano do guloso do artigo e as demais sorteadas (cada motorista fica com
probabilidade p_ficar). Avaliação J nos pseudodias de busca; escolha final entre guloso, gbest e vazio nos
pseudodias de aceitação. Prioridade baixa: entra para completude com orçamento fixo (partículas × iterações).
"""

from __future__ import annotations

from tcc_frota.algoritmos.base import Moves, PlanContext, Planner
from tcc_frota.algoritmos.busca_local import ARTICLE_GREEDY, start_plan
from tcc_frota.algoritmos.cenarios import Evaluator, Neighborhood, accept_on_holdout, seeded_rng, split, to_moves, zone_plan

C1 = C2 = 1.5
MAX_CANDIDATES = 8


class EnxameParticulas(Planner):
    family = "pso"
    stochastic = True
    needs_scenarios = True

    def __init__(self, p_ficar: float, inercia: float, particulas: int, iteracoes: int, max_km: float):
        super().__init__(max_km)
        self.p_ficar, self.inercia, self.particulas, self.iteracoes = p_ficar, inercia, particulas, iteracoes

    @property
    def params(self) -> dict:
        return {
            "p_ficar": self.p_ficar,
            "inercia": self.inercia,
            "particulas": self.particulas,
            "iteracoes": self.iteracoes,
            "max_km": self.max_km,
        }

    def plan(self, ctx: PlanContext) -> Moves:
        rng = seeded_rng(ctx, salt=8)
        search, hold = split(ctx.scenarios)
        nb = Neighborhood(ctx, self.max_km, rng, MAX_CANDIDATES)
        if not search or not nb.movable:
            self.info = {"status": "sem_pseudodias_ou_candidatos"}
            return {}
        ids = nb.movable
        k = {d: len(nb.cands[d]) for d in ids}
        ev = Evaluator(ctx, search, self.max_km)

        def decode(x: dict[str, float]) -> dict[str, str]:
            out = {}
            for d in ids:
                idx = int(x[d])
                if idx >= 1:
                    out[d] = nb.cands[d][min(idx, k[d]) - 1][0]
            return out

        greedy = zone_plan(ctx, start_plan(ctx, "guloso", None))
        swarm = []
        for p in range(self.particulas):
            x = {}
            for d in ids:
                if p == 0:
                    x[d] = 0.5
                elif p == 1:
                    z = greedy.get(d)
                    pos = [c for c, _ in nb.cands[d]]
                    x[d] = pos.index(z) + 1.5 if z in pos else 0.5
                else:
                    x[d] = 0.5 if rng.random() < self.p_ficar else rng.uniform(1, k[d] + 1)
            v = {d: rng.uniform(-1, 1) for d in ids}
            swarm.append({"x": x, "v": v, "best": dict(x), "f": ev.objective(decode(x))})
            swarm[-1]["fbest"] = swarm[-1]["f"]
        g = min(swarm, key=lambda s: s["fbest"])
        gbest, fg = dict(g["best"]), g["fbest"]
        evaluations = self.particulas
        for _ in range(self.iteracoes - 1):
            for s in swarm:
                for d in ids:
                    lim = (k[d] + 1) / 2
                    vel = (
                        self.inercia * s["v"][d]
                        + C1 * rng.random() * (s["best"][d] - s["x"][d])
                        + C2 * rng.random() * (gbest[d] - s["x"][d])
                    )
                    s["v"][d] = max(-lim, min(lim, vel))
                    s["x"][d] = max(0.0, min(k[d] + 1 - 1e-9, s["x"][d] + s["v"][d]))
                s["f"] = ev.objective(decode(s["x"]))
                evaluations += 1
                if s["f"] < s["fbest"] - 1e-12:
                    s["best"], s["fbest"] = dict(s["x"]), s["f"]
                    if s["f"] < fg - 1e-12:
                        gbest, fg = dict(s["x"]), s["f"]
        best = decode(gbest)
        greedy = {d: z for d, z in greedy.items() if (d, z) in nb.km}
        chosen, scores = accept_on_holdout(ctx, hold, self.max_km, {"inicial": greedy, "melhor": best, "vazio": {}})
        plan = {"inicial": greedy, "melhor": best, "vazio": {}}[chosen]
        self.info = {
            "status": "ok",
            "avaliacoes": evaluations,
            "J_busca_melhor": fg,
            "J_busca_vazio": ev.objective({}),
            "J_busca_inicial": ev.objective(greedy),
            "escolhido": chosen,
            "movimentos_melhor": len(best),
            "simulacoes": ev.simulations,
            **scores,
        }
        return to_moves(ctx, plan, nb)


__all__ = ["ARTICLE_GREEDY", "EnxameParticulas"]
