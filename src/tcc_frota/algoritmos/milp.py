r"""5.3 MILP min(B + R) com piso de atendimento (HiGHS via `scipy.optimize.milp`).

Conjuntos: motoristas i do plano, cada um com posição atual o_i; posições candidatas
C_i = {o_i} ∪ {centróides z : km(o_i, z) ≤ H}; posições P = ∪ C_i; zonas z com demanda λ_z > 0
(previsão da janela). d_pz = reta(p, z) × fator rua/reta; r = raio de despacho do simulador (reta).

Variáveis: y_ip ∈ {0, 1} (posição escolhida); g_pz ≥ 0 (corridas esperadas da zona z atendidas por
veículos na posição p, só se reta(p, z) ≤ r).

    min  Σ_pz d_pz g_pz  +  Σ_i Σ_p (km_ip + μ·[p ≠ o_i]) y_ip
    s.a. Σ_p y_ip = 1                         ∀ i
         Σ_p g_pz ≤ λ_z                       ∀ z     (cobertura ≤ 1 por zona)
         Σ_z g_pz ≤ cap · Σ_i y_ip            ∀ p     (capacidade de corridas por veículo)
         Σ_pz g_pz ≥ β · S0                           (piso: S0 = máximo atendível sem mover, por PL)

`cap` = corridas por veículo na janela; cap ≈ 1 representa a hipótese da "primeira corrida".
Com S cenários de demanda (5.7), g ganha o índice s, cada cenário tem piso próprio
(β · S0_s) e o objetivo é o valor esperado ou o CVaR_a de custo_s = B_s + R (Rockafellar–Uryasev:
t + Σ_s u_s / ((1 − a)S), u_s ≥ custo_s − t, u ≥ 0). O ótimo do modelo não é o ótimo do simulador: o
modelo é estático e supõe que cada veículo atende `cap` corridas da posição escolhida.
"""

from __future__ import annotations

import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix

from tcc_frota.algoritmos.alvos import window_demand
from tcc_frota.algoritmos.base import Moves, PlanContext, Planner
from tcc_frota.v2.policy import PlanInputs
from tcc_frota.v2.sim import reta_km


def _positions(inp: PlanInputs, hop: float):
    """Posições candidatas: casa de cada motorista e centróides ao alcance do salto."""
    pos: list[tuple[float, float]] = []
    index: dict[tuple, int] = {}

    def add(key, latlon):
        if key not in index:
            index[key] = len(pos)
            pos.append(latlon)
        return index[key]

    cands: list[list[tuple[int, float, str | None]]] = []  # (posição, km, zona-destino)
    for d in inp.drivers:
        opts = [(add(("casa", d.did), (d.lat, d.lon)), 0.0, None)]
        for z, c in inp.zones.items():
            km = reta_km(d.lat, d.lon, *c) * inp.road_factor
            if 1e-9 < km <= hop + 1e-9:
                opts.append((add(("zona", z), c), km, z))
        cands.append(opts)
    return pos, cands


def max_served_without_moves(pos, home_idx: list[int], lam: dict[str, float], zones, radius: float, cap: float) -> float:
    """S0: corridas esperadas atendíveis com todos na posição atual (PL)."""
    arcs = [(p, z) for p in sorted(set(home_idx)) for z in lam if reta_km(*pos[p], *zones[z]) <= radius]
    if not arcs:
        return 0.0
    count = {p: home_idx.count(p) for p in set(home_idx)}
    rows, cols = [], []
    zi = {z: k for k, z in enumerate(sorted(lam))}
    pi = {p: k for k, p in enumerate(sorted(set(home_idx)))}
    for k, (p, z) in enumerate(arcs):
        rows += [zi[z], len(zi) + pi[p]]
        cols += [k, k]
    a = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(zi) + len(pi), len(arcs))).tocsr()
    b = [lam[z] for z in sorted(lam)] + [cap * count[p] for p in sorted(set(home_idx))]
    res = linprog(-np.ones(len(arcs)), A_ub=a, b_ub=b, bounds=(0, None), method="highs")
    return float(-res.fun) if res.status == 0 else 0.0


def solve(
    inp: PlanInputs,
    lams: list[dict[str, float]],
    *,
    cap: float,
    beta: float,
    mu: float,
    hop: float,
    radius: float,
    objective: str = "esperado",
    cvar_alpha: float = 0.8,
    time_limit: float = 30.0,
) -> tuple[Moves, dict]:
    started = time.perf_counter()
    lams = [{z: v for z, v in lam.items() if v > 0 and z in inp.zones} for lam in lams]
    if not inp.drivers or not any(lams):
        return {}, {"status": "vazio"}
    pos, cands = _positions(inp, hop)
    home_idx = [c[0][0] for c in cands]
    n_s = len(lams)
    # variáveis y
    y_meta = [(i, p, km, z) for i, opts in enumerate(cands) for p, km, z in opts]
    n_y = len(y_meta)
    # variáveis g por cenário
    g_meta: list[list[tuple[int, str, float]]] = []
    for lam in lams:
        g_meta.append(
            [
                (p, z, reta_km(*pos[p], *inp.zones[z]) * inp.road_factor)
                for p in range(len(pos))
                for z in sorted(lam)
                if reta_km(*pos[p], *inp.zones[z]) <= radius
            ]
        )
    offs = [n_y]
    for gm in g_meta:
        offs.append(offs[-1] + len(gm))
    n_g_total = offs[-1] - n_y
    cvar = objective == "cvar"
    n_var = offs[-1] + (1 + n_s if cvar else 0)
    t_idx = offs[-1]
    c = np.zeros(n_var)
    repo_cost = np.array([km + (mu if z is not None else 0.0) for _, _, km, z in y_meta])
    if cvar:
        c[t_idx] = 1.0
        c[t_idx + 1 :] = 1.0 / ((1 - cvar_alpha) * n_s)
    else:
        c[:n_y] = repo_cost
        for s, gm in enumerate(g_meta):
            c[offs[s] : offs[s + 1]] = [d / n_s for _, _, d in gm]
    rows, cols, vals, lb, ub = [], [], [], [], []
    r = 0

    def add_row(entries, lo, hi):
        nonlocal r
        for col, v in entries:
            rows.append(r)
            cols.append(col)
            vals.append(v)
        lb.append(lo)
        ub.append(hi)
        r += 1

    for i in range(len(cands)):
        add_row([(k, 1.0) for k, m in enumerate(y_meta) if m[0] == i], 1.0, 1.0)
    y_by_pos: dict[int, list[int]] = {}
    for k, (_, p, _, _) in enumerate(y_meta):
        y_by_pos.setdefault(p, []).append(k)
    s0s = []
    for s, (lam, gm) in enumerate(zip(lams, g_meta)):
        by_z: dict[str, list[int]] = {}
        by_p: dict[int, list[int]] = {}
        for k, (p, z, _) in enumerate(gm):
            by_z.setdefault(z, []).append(offs[s] + k)
            by_p.setdefault(p, []).append(offs[s] + k)
        for z, ks in by_z.items():
            add_row([(k, 1.0) for k in ks], -np.inf, lam[z])
        for p, ks in by_p.items():
            add_row([(k, 1.0) for k in ks] + [(k, -cap) for k in y_by_pos.get(p, [])], -np.inf, 0.0)
        s0 = max_served_without_moves(pos, home_idx, lam, inp.zones, radius, cap)
        s0s.append(s0)
        add_row([(offs[s] + k, 1.0) for k in range(len(gm))], beta * s0 - 1e-6, np.inf)
        if cvar:  # u_s - B_s - R + t >= 0
            add_row(
                [(offs[s] + k, -d) for k, (_, _, d) in enumerate(gm)]
                + [(k, -repo_cost[k]) for k in range(n_y)]
                + [(t_idx, 1.0), (t_idx + 1 + s, 1.0)],
                0.0,
                np.inf,
            )
    a = coo_matrix((vals, (rows, cols)), shape=(r, n_var)).tocsr()
    integrality = np.zeros(n_var)
    integrality[:n_y] = 1
    lo = np.zeros(n_var)
    hi = np.full(n_var, np.inf)
    hi[:n_y] = 1.0
    if cvar:
        lo[t_idx] = -np.inf
    res = milp(
        c,
        constraints=LinearConstraint(a, lb, ub),
        integrality=integrality,
        bounds=Bounds(lo, hi),
        options={"time_limit": time_limit, "mip_rel_gap": 1e-4, "disp": False},
    )
    info = {
        "status": res.status,
        "mensagem": str(res.message)[:80],
        "gap": getattr(res, "mip_gap", None),
        "variaveis_binarias": n_y,
        "variaveis_continuas": n_g_total,
        "restricoes": r,
        "S0": s0s,
        "segundos_solver": time.perf_counter() - started,
    }
    if res.x is None:
        info["resultado"] = "sem solução: plano vazio"
        return {}, info
    x = res.x
    moves: Moves = {}
    for k, (i, p, km, z) in enumerate(y_meta):
        if z is not None and x[k] > 0.5:
            d = inp.drivers[i]
            moves[d.did] = (inp.zones[z][0], inp.zones[z][1], km)
    served = [float(x[offs[s] : offs[s + 1]].sum()) for s in range(n_s)]
    pickup = [float(sum(x[offs[s] + k] * d for k, (_, _, d) in enumerate(gm))) for s, gm in enumerate(g_meta)]
    info.update(
        {
            "objetivo": float(res.fun),
            "atendidas_modelo": served,
            "busca_modelo_km": pickup,
            "repos_modelo_km": sum(m[2] for m in moves.values()),
        }
    )
    return moves, info


class MILPBuscaReposicionamento(Planner):
    family = "milp"

    def __init__(self, cap: float, beta: float, mu: float, max_km: float, time_limit: float = 30.0):
        super().__init__(max_km)
        self.cap, self.beta, self.mu, self.time_limit = cap, beta, mu, time_limit

    @property
    def params(self) -> dict:
        return {"cap": self.cap, "beta": self.beta, "mu": self.mu, "max_km": self.max_km, "time_limit": self.time_limit}

    def plan(self, ctx: PlanContext) -> Moves:
        moves, self.info = solve(
            ctx.inputs,
            [window_demand(ctx.inputs)],
            cap=self.cap,
            beta=self.beta,
            mu=self.mu,
            hop=self.max_km,
            radius=ctx.sim.radius_km,
            time_limit=self.time_limit,
        )
        return moves
