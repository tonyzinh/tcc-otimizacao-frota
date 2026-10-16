"""Alvos de motoristas por zona (H3 r7) a partir da demanda prevista no corte.

- `demanda`: alvo_z ∝ λ_z, total = round(share × N).
- `valor_marginal`: vagas uma a uma para a zona de maior ganho marginal
  ΔV_z(n) = min(λ_z, c·(n+1)) − min(λ_z, c·n), com c = κ × horas da janela (corridas que um motorista
  atende na janela); para quando nenhuma vaga acrescenta valor. É o mesmo valor esperado do guloso.
- `misto`: (1 − w)·demanda + w·valor marginal, para o planejador paramétrico do NSGA-II.
Um teto opcional limita o alvo por zona. Nenhum alvo é política da empresa (RN019).
"""
from __future__ import annotations

import heapq
from collections import Counter

from tcc_frota.v2.policy import PlanInputs
from tcc_frota.v2.sim import reta_km


def window_demand(inputs: PlanInputs) -> dict[str, float]:
    out: dict[str, float] = {}
    for (_, z), v in inputs.demand.items():
        if z in inputs.zones and v > 0:
            out[z] = out.get(z, 0.0) + v
    return out


def nearest_zone(lat: float, lon: float, zones: dict[str, tuple[float, float]]) -> str:
    return min(zones, key=lambda z: (reta_km(lat, lon, *zones[z]), z))


def driver_zones(inputs: PlanInputs) -> dict[str, str]:
    return {d.did: nearest_zone(d.lat, d.lon, inputs.zones) for d in inputs.drivers}


def largest_remainder(real: dict[str, float], total: int) -> dict[str, int]:
    total = max(0, total)
    base = {z: int(v) for z, v in real.items()}
    rest = total - sum(base.values())
    for z in sorted(real, key=lambda z: (-(real[z] - base[z]), z))[:max(0, rest)]:
        base[z] += 1
    return {z: n for z, n in base.items() if n > 0}


def demand_targets(lam: dict[str, float], total: int) -> dict[str, float]:
    s = sum(lam.values())
    return {z: total * v / s for z, v in lam.items()} if s > 0 else {}


def marginal_targets(lam: dict[str, float], total: int, per_driver: float) -> dict[str, int]:
    """Preenchimento por valor marginal (concavo em n, então o guloso é ótimo para o valor esperado)."""
    counts: Counter = Counter()
    if per_driver <= 0:
        return {}
    heap = [(-min(v, per_driver), z) for z, v in lam.items() if v > 0]
    heapq.heapify(heap)
    for _ in range(max(0, total)):
        if not heap:
            break
        neg, z = heapq.heappop(heap)
        if -neg <= 1e-12:
            break
        counts[z] += 1
        n = counts[z]
        nxt = min(lam[z], per_driver * (n + 1)) - min(lam[z], per_driver * n)
        heapq.heappush(heap, (-nxt, z))
    return dict(counts)


def targets(inputs: PlanInputs, kind: str, share: float, cap: int | None = None, weight: float = 0.5) -> dict[str, int]:
    lam = window_demand(inputs)
    total = int(round(share * len(inputs.drivers)))
    per_driver = inputs.kappa * len(inputs.hours)
    if kind == "demanda":
        out = largest_remainder(demand_targets(lam, total), total)
    elif kind == "valor_marginal":
        out = marginal_targets(lam, total, per_driver)
    elif kind == "teto":
        out = largest_remainder(demand_targets(lam, total), total)
        cap = 2 if cap is None else cap
    elif kind == "misto":
        dem = demand_targets(lam, total)
        vm = marginal_targets(lam, total, per_driver)
        real = {z: (1 - weight) * dem.get(z, 0.0) + weight * vm.get(z, 0) for z in set(dem) | set(vm)}
        out = largest_remainder(real, int(round(sum(real.values()))))
    else:
        raise ValueError(f"alvo desconhecido: {kind}")
    if cap is not None:
        out = {z: min(n, cap) for z, n in out.items()}
    return {z: n for z, n in out.items() if n > 0}


def surplus_deficit(have: dict[str, int], target: dict[str, int]) -> tuple[dict[str, int], dict[str, int]]:
    zones = set(have) | set(target)
    sup = {z: have.get(z, 0) - target.get(z, 0) for z in zones if have.get(z, 0) > target.get(z, 0)}
    dem = {z: target.get(z, 0) - have.get(z, 0) for z in zones if target.get(z, 0) > have.get(z, 0)}
    return sup, dem
