r"""5.7 Otimização robusta por cenários de demanda (MILP de 5.3 com S cenários).

Cenários: S reamostragens com reposição dos dias de treino do mesmo dia da semana anteriores a D;
λ^s_z = pedidos observados da zona z na janela naquele dia. As decisões de posição y são comuns a todos
os cenários; cada cenário tem atribuição g^s e piso próprio (β · S0_s). Objetivo: valor esperado de
B_s + R ou CVaR₀,₈ de B_s + R (formulação em `milp.py`). cap, β e μ vêm do finalista de 5.3 (pré-registro).
O sorteio dos cenários depende da semente; o resultado no simulador é a média das 5 sementes por dia.
"""
from __future__ import annotations

from collections import Counter

from tcc_frota.algoritmos.base import Moves, PlanContext, Planner
from tcc_frota.algoritmos.cenarios import seeded_rng
from tcc_frota.algoritmos.milp import solve


def scenario_demand(ctx: PlanContext, n: int, rng) -> list[dict[str, float]]:
    pool = [Counter(r.zone for r in s.requests if r.zone in ctx.inputs.zones) for s in ctx.scenarios]
    pool = [p for p in pool if p]
    if not pool:
        return []
    return [dict(pool[rng.randrange(len(pool))]) for _ in range(n)]


class MILPCenarios(Planner):
    family = "robusto_cenarios"
    stochastic = True
    needs_scenarios = True

    def __init__(self, n_cenarios: int, objetivo: str, cap: float, beta: float, mu: float, max_km: float,
                 time_limit: float = 60.0):
        super().__init__(max_km)
        if objetivo not in ("esperado", "cvar"):
            raise ValueError(objetivo)
        self.n_cenarios, self.objetivo, self.cap, self.beta, self.mu, self.time_limit = n_cenarios, objetivo, cap, beta, mu, time_limit

    @property
    def params(self) -> dict:
        return {"n_cenarios": self.n_cenarios, "objetivo": self.objetivo, "cap": self.cap, "beta": self.beta,
                "mu": self.mu, "max_km": self.max_km, "time_limit": self.time_limit}

    def plan(self, ctx: PlanContext) -> Moves:
        lams = scenario_demand(ctx, self.n_cenarios, seeded_rng(ctx, salt=7))
        if not lams:
            self.info = {"status": "sem_pseudodias"}
            return {}
        moves, info = solve(ctx.inputs, lams, cap=self.cap, beta=self.beta, mu=self.mu, hop=self.max_km,
                            radius=ctx.sim.radius_km, objective=self.objetivo, time_limit=self.time_limit)
        self.info = {k: v for k, v in info.items() if k not in ("atendidas_modelo", "busca_modelo_km", "S0")}
        self.info["cenarios"] = len(lams)
        return moves
