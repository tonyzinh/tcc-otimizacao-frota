r"""5.2 Método húngaro com posições de espera.

Posições de espera = vagas-alvo nos centróides das zonas (`alvos.targets`, os mesmos alvos de 5.1).
Matriz de custo motorista i × coluna j, com N colunas "livre" (custo 0, não mexe) e uma coluna por vaga:

    c_ij = −P                    se a vaga j é da zona atual de i (fica onde está e preenche a vaga)
    c_ij = km(i, centróide_j) − P se km ≤ H (salto máximo)
    c_ij = proibido              caso contrário

`scipy.optimize.linear_sum_assignment` minimiza Σ c: com P grande, maximiza as vagas preenchidas e, entre
as soluções com o máximo de vagas, minimiza o km dos movimentos. Diferença para 5.1: o custo é medido do
motorista (não do centróide da zona dele) até a vaga e a escolha de quem se move é ótima, não gulosa.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment

from tcc_frota.algoritmos.alvos import driver_zones, targets
from tcc_frota.algoritmos.base import Moves, PlanContext, Planner
from tcc_frota.v2.sim import reta_km

FILL_REWARD = 1000.0
FORBIDDEN = 1e9


class HungaroPosicoesEspera(Planner):
    family = "hungaro"

    def __init__(self, alvo: str, share: float, max_km: float, teto: int | None = None):
        super().__init__(max_km)
        self.alvo, self.share, self.teto = alvo, share, teto

    @property
    def params(self) -> dict:
        return {"alvo": self.alvo, "share": self.share, "max_km": self.max_km, "teto": self.teto}

    def plan(self, ctx: PlanContext) -> Moves:
        inp = ctx.inputs
        if not inp.drivers or not inp.zones:
            self.info = {"status": "vazio"}
            return {}
        slots = [z for z, n in sorted(targets(inp, self.alvo, self.share, self.teto).items()) for _ in range(n)]
        zone_of = driver_zones(inp)
        drivers = sorted(inp.drivers, key=lambda d: d.did)
        n = len(drivers)
        cost = np.zeros((n, len(slots) + n))
        km = np.zeros((n, len(slots)))
        for i, d in enumerate(drivers):
            for j, z in enumerate(slots):
                if zone_of[d.did] == z:
                    cost[i, j] = -FILL_REWARD
                else:
                    km[i, j] = reta_km(d.lat, d.lon, *inp.zones[z]) * inp.road_factor
                    cost[i, j] = km[i, j] - FILL_REWARD if km[i, j] <= self.max_km + 1e-9 else FORBIDDEN
        rows, cols = linear_sum_assignment(cost)
        moves: Moves = {}
        filled = 0
        for i, j in zip(rows, cols):
            if j >= len(slots) or cost[i, j] >= FORBIDDEN:
                continue
            filled += 1
            d, z = drivers[i], slots[j]
            if zone_of[d.did] != z and km[i, j] > 1e-9:
                moves[d.did] = (inp.zones[z][0], inp.zones[z][1], float(km[i, j]))
        self.info = {"status": "otimo", "vagas": len(slots), "vagas_preenchidas": filled, "movimentos": len(moves),
                     "objetivo_km": sum(m[2] for m in moves.values())}
        return moves
