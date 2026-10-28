r"""5.9 MPC / horizonte deslizante — **cenário intradiário, fora do escopo D+1** (tabela própria).

A cada 30 min da janela, o planejador vê o estado em tempo real (motoristas livres e posição; ocupados,
com hora e posição em que ficam livres) e a previsão D+1 por zona-hora feita no corte, e decide
reposicionamentos imediatos dos **livres** para as próximas H horas com o mesmo valor esperado do guloso
de valor marginal: movimento de maior ΔV − α·km, até o saldo ficar ≤ 0. Os ocupados contam na cobertura
a partir da hora em que ficam livres, mas não são movidos. A demanda da hora corrente é proporcional ao
trecho restante do horizonte. Usa informação de D+1 em tempo real (estado da frota), por isso não entra
na tabela principal.
"""

from __future__ import annotations

from math import ceil, floor

from tcc_frota.v2.fleet import PlannedDriver
from tcc_frota.v2.policy import PlanInputs, _Coverage, home_zone
from tcc_frota.v2.sim import reta_km

EPOCH_S = 1800.0


def epoch_times(window: tuple[int, int]) -> tuple[float, ...]:
    w0, w1 = window[0] * 3600.0, window[1] * 3600.0
    out, t = [], w0
    while t < w1:
        out.append(t)
        t += EPOCH_S
    return tuple(out)


def plan_epoch(
    t: float,
    idle: dict[str, tuple[float, float]],
    busy: dict[str, tuple[float, tuple[float, float]]],
    base: PlanInputs,
    window: tuple[int, int],
    *,
    horizon_h: float,
    alpha: float,
    rho_km: float,
    max_km: float,
) -> dict[str, tuple[float, float]]:
    if not idle:
        return {}
    t_end = min(t + horizon_h * 3600.0, window[1] * 3600.0)
    hours = tuple(h for h in range(floor(t / 3600), ceil(t_end / 3600)) if window[0] <= h < window[1])
    demand = {}
    for (h, z), v in base.demand.items():
        if h in hours:
            overlap = max(0.0, min(h + 1, t_end / 3600) - max(h, t / 3600))
            if overlap > 0:
                demand[(h, z)] = v * overlap
    drivers = [PlannedDriver(did, p[0], p[1], t / 3600, t_end / 3600) for did, p in sorted(idle.items())]
    drivers += [
        PlannedDriver(did, p[0], p[1], min(free_at, t_end) / 3600, t_end / 3600)
        for did, (free_at, p) in sorted(busy.items())
        if p is not None
    ]
    inp = PlanInputs(tuple(drivers), base.zones, demand, hours, base.kappa, base.road_factor)
    cov = _Coverage(inp)
    home = {d.did: home_zone(d.lat, d.lon, inp.zones, rho_km) for d in drivers}
    for did, z in home.items():
        cov.apply(did, z, +1)
    targets = sorted({z for (_, z), v in demand.items() if v > 0 and z in inp.zones})
    pos = {d.did: (d.lat, d.lon) for d in drivers}
    moves: dict[str, tuple[float, float]] = {}
    movable = sorted(idle)
    while True:
        best = None
        for did in movable:
            if did in moves:
                continue
            loss = cov.delta_remove(did, home[did])
            for z in targets:
                if z == home[did]:
                    continue
                km = reta_km(*pos[did], *inp.zones[z]) * inp.road_factor
                if km > max_km or km <= 1e-9:
                    continue
                score = cov.delta_add(did, z) - loss - alpha * km
                if best is None or score > best[0] + 1e-12:
                    best = (score, did, z)
        if best is None or best[0] <= 1e-12:
            break
        _, did, z = best
        cov.apply(did, home[did], -1)
        cov.apply(did, z, +1)
        home[did] = z
        moves[did] = inp.zones[z]
    return moves
