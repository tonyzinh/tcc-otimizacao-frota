r"""5.1 Fluxo de custo mínimo entre zonas H3 r7 (e o planejador paramétrico do NSGA-II).

Formulação (transporte com folga). Zonas u com excedente s_u = max(0, tem_u − alvo_u) e zonas v com
déficit d_v = max(0, alvo_v − tem_v), onde tem_u conta os motoristas do plano cujo centróide mais
próximo é u e alvo vem de `alvos.targets`. Custo c_uv = reta(centróide_u, centróide_v) × fator
rua/reta, só para c_uv ≤ H (salto máximo):

    min  Σ_uv c_uv f_uv + P Σ_v ω_v
    s.a. Σ_v f_uv ≤ s_u          (excedente)
         Σ_u f_uv + ω_v = d_v    (déficit; ω = déficit não preenchido)
         f, ω ≥ 0

A matriz é de incidência de rede (totalmente unimodular): o simplex dual do HiGHS devolve solução
inteira. Com P = 1.000 km, todo déficit alcançável é preenchido. Cada unidade de fluxo u→v vira um
movimento do motorista da zona u mais próximo do centróide de v cujo deslocamento real respeita H.
Resolve com `scipy.optimize.linprog` (sem dependência nova).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix

from tcc_frota.algoritmos.alvos import driver_zones, surplus_deficit, targets
from tcc_frota.algoritmos.base import Moves, PlanContext, Planner
from tcc_frota.v2.policy import PlanInputs
from tcc_frota.v2.sim import reta_km

UNMET_PENALTY = 1000.0


def solve_transport(inputs: PlanInputs, sup: dict[str, int], dem: dict[str, int], hop: float) -> tuple[dict[tuple[str, str], int], dict]:
    zones = inputs.zones
    arcs = [(u, v, reta_km(*zones[u], *zones[v]) * inputs.road_factor) for u in sorted(sup) for v in sorted(dem)]
    arcs = [a for a in arcs if a[2] <= hop + 1e-9]
    if not arcs:
        return {}, {"status": "sem_arcos", "objetivo_km": 0.0, "deficit_nao_preenchido": sum(dem.values())}
    dv = sorted(dem)
    n_f, n_w = len(arcs), len(dv)
    cost = np.array([a[2] for a in arcs] + [UNMET_PENALTY] * n_w)
    su = sorted(sup)
    a_ub = lil_matrix((len(su), n_f + n_w))
    a_eq = lil_matrix((n_w, n_f + n_w))
    iu = {u: k for k, u in enumerate(su)}
    iv = {v: k for k, v in enumerate(dv)}
    for k, (u, v, _) in enumerate(arcs):
        a_ub[iu[u], k] = 1
        a_eq[iv[v], k] = 1
    for k, v in enumerate(dv):
        a_eq[k, n_f + k] = 1
    res = linprog(cost, A_ub=a_ub.tocsr(), b_ub=[sup[u] for u in su], A_eq=a_eq.tocsr(), b_eq=[dem[v] for v in dv],
                  bounds=(0, None), method="highs-ds")
    if res.status != 0:
        return {}, {"status": f"falha_{res.status}", "objetivo_km": float("nan"), "deficit_nao_preenchido": sum(dem.values())}
    flows = {(u, v): int(round(x)) for (u, v, _), x in zip(arcs, res.x[:n_f]) if x > 0.5}
    unmet = float(res.x[n_f:].sum())
    return flows, {"status": "otimo", "objetivo_km": float(sum(c * res.x[k] for k, (_, _, c) in enumerate(arcs))),
                   "deficit_nao_preenchido": unmet}


def flows_to_moves(inputs: PlanInputs, flows: dict[tuple[str, str], int], hop: float, min_km: float = 0.0) -> Moves:
    zone_of = driver_zones(inputs)
    by_zone: dict[str, list] = {}
    for d in inputs.drivers:
        by_zone.setdefault(zone_of[d.did], []).append(d)
    used: set[str] = set()
    moves: Moves = {}
    for (u, v), k in sorted(flows.items(), key=lambda kv: kv[0]):
        c = inputs.zones[v]
        cands = sorted(((reta_km(d.lat, d.lon, *c) * inputs.road_factor, d.did) for d in by_zone.get(u, ())
                        if d.did not in used))
        for km, did in cands:
            if k <= 0:
                break
            if km > hop + 1e-9:
                break
            used.add(did)
            k -= 1
            if km >= max(min_km, 1e-9):
                moves[did] = (c[0], c[1], km)
    return moves


class FluxoCustoMinimo(Planner):
    family = "fluxo_custo_minimo"

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
        target = targets(inp, self.alvo, self.share, self.teto)
        have: dict[str, int] = {}
        for z in driver_zones(inp).values():
            have[z] = have.get(z, 0) + 1
        sup, dem = surplus_deficit(have, target)
        flows, info = solve_transport(inp, sup, dem, self.max_km)
        moves = flows_to_moves(inp, flows, self.max_km)
        self.info = {**info, "alvo_total": sum(target.values()), "excedente": sum(sup.values()),
                     "deficit": sum(dem.values()), "fluxo": sum(flows.values()), "movimentos": len(moves)}
        return moves


class FluxoParametrico(Planner):
    """Planejador paramétrico buscado pelo NSGA-II (5.6): alvo misto, share, H, teto e km mínimo."""

    family = "nsga2"

    def __init__(self, peso: float, share: float, max_km: float, teto: int | None, km_min: float):
        super().__init__(max_km)
        self.peso, self.share, self.teto, self.km_min = peso, share, teto, km_min

    @property
    def params(self) -> dict:
        return {"peso": self.peso, "share": self.share, "max_km": self.max_km, "teto": self.teto, "km_min": self.km_min}

    def plan(self, ctx: PlanContext) -> Moves:
        inp = ctx.inputs
        if not inp.drivers or not inp.zones:
            self.info = {"status": "vazio"}
            return {}
        target = targets(inp, "misto", self.share, self.teto, self.peso)
        have: dict[str, int] = {}
        for z in driver_zones(inp).values():
            have[z] = have.get(z, 0) + 1
        sup, dem = surplus_deficit(have, target)
        flows, info = solve_transport(inp, sup, dem, self.max_km)
        moves = flows_to_moves(inp, flows, self.max_km, self.km_min)
        self.info = {**info, "movimentos": len(moves)}
        return moves
