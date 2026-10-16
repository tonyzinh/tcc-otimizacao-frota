"""Planejadores D+1 da v2 (Fase 5). Todos recebem as mesmas entradas do corte.

Valor esperado de uma configuração da frota (proxy interpretável, não verdade): cada motorista
planejado é associado à zona H3 r7 de centróide mais próximo dentro de `rho_km`; em cada zona e hora,
corridas atendidas esperadas = min(λ_zona,hora, κ × motoristas presentes na zona naquela hora), com
κ = corridas por motorista-hora calibradas no treino. O replay é quem mede o efeito real.

- `marginal_greedy`: a cada passo escolhe o movimento com maior (ganho esperado − α × km por rua) e
  para quando o melhor saldo é ≤ 0. α é o preço implícito do km em corridas; variar α traça a fronteira.
- `threshold_rule`: cada motorista, isoladamente, vai à zona de maior ganho por km se ganho/km ≥ θ.
- `proportional`: vagas proporcionais à demanda prevista, preenchidas pelo par mais próximo.
Nenhum é política da empresa; limites são parâmetros experimentais (RN019).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from tcc_frota.optimization.alternatives import target_slots
from tcc_frota.v2.fleet import PlannedDriver
from tcc_frota.v2.sim import reta_km


@dataclass(frozen=True)
class PlanInputs:
    drivers: tuple[PlannedDriver, ...]
    zones: dict[str, tuple[float, float]]        # centróide ponderado pela demanda do treino
    demand: dict[tuple[int, str], float]         # λ[(hora, zona)] previsto para a janela
    hours: tuple[int, ...]
    kappa: float                                 # corridas por motorista-hora
    road_factor: float


@dataclass
class Plan:
    moves: dict[str, tuple[float, float]]
    expected_gain: float
    planned_km: float
    steps: int = 0


def _presence(d: PlannedDriver, hours: tuple[int, ...]) -> dict[int, float]:
    return {h: max(0.0, min(d.end_h, h + 1) - max(d.start_h, h)) for h in hours}


class _Coverage:
    """Estado incremental do valor esperado por zona."""

    def __init__(self, inputs: PlanInputs):
        self.inp = inputs
        self.load: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
        self.pres = {d.did: _presence(d, inputs.hours) for d in inputs.drivers}

    def zone_value(self, zone: str, load: dict[int, float]) -> float:
        k = self.inp.kappa
        return sum(min(self.inp.demand.get((h, zone), 0.0), k * load.get(h, 0.0)) for h in self.inp.hours)

    def delta_add(self, did: str, zone: str | None) -> float:
        if zone is None:
            return 0.0
        cur = self.load[zone]
        new = {h: cur.get(h, 0.0) + self.pres[did][h] for h in self.inp.hours}
        return self.zone_value(zone, new) - self.zone_value(zone, cur)

    def delta_remove(self, did: str, zone: str | None) -> float:
        if zone is None:
            return 0.0
        cur = self.load[zone]
        new = {h: cur.get(h, 0.0) - self.pres[did][h] for h in self.inp.hours}
        return self.zone_value(zone, cur) - self.zone_value(zone, new)

    def apply(self, did: str, zone: str | None, sign: float) -> None:
        if zone is None:
            return
        for h in self.inp.hours:
            self.load[zone][h] += sign * self.pres[did][h]


def home_zone(lat: float, lon: float, zones: dict[str, tuple[float, float]], rho_km: float) -> str | None:
    best = min(((reta_km(lat, lon, *c), z) for z, c in zones.items()), default=None)
    return best[1] if best and best[0] <= rho_km else None


def _targets(inputs: PlanInputs) -> list[str]:
    total = defaultdict(float)
    for (h, z), v in inputs.demand.items():
        total[z] += v
    return sorted(z for z, v in total.items() if v > 0 and z in inputs.zones)


def marginal_greedy(inputs: PlanInputs, *, alpha: float, rho_km: float, max_km: float) -> Plan:
    cov = _Coverage(inputs)
    home = {d.did: home_zone(d.lat, d.lon, inputs.zones, rho_km) for d in inputs.drivers}
    for did, z in home.items():
        cov.apply(did, z, +1)
    targets = _targets(inputs)
    by_id = {d.did: d for d in inputs.drivers}
    dist = {(d.did, z): reta_km(d.lat, d.lon, *inputs.zones[z]) * inputs.road_factor
            for d in inputs.drivers for z in targets}
    moves: dict[str, tuple[float, float]] = {}
    gain_total = km_total = 0.0
    steps = 0
    candidates = {did: [z for z in targets if z != home[did] and dist[(did, z)] <= max_km] for did in by_id}
    add_cache: dict[tuple[str, str], float] = {}
    loss_cache: dict[str, float] = {}
    while True:
        best = None
        for did in sorted(by_id):
            if did in moves:
                continue
            if did not in loss_cache:
                loss_cache[did] = cov.delta_remove(did, home[did])
            for z in candidates[did]:
                key = (did, z)
                if key not in add_cache:
                    add_cache[key] = cov.delta_add(did, z)
                km = dist[key]
                score = add_cache[key] - loss_cache[did] - alpha * km
                if best is None or score > best[0] + 1e-12:
                    best = (score, key, km)
        if best is None or best[0] <= 1e-12:
            break
        _, (did, z), km = best
        old = home[did]
        gain_total += add_cache[(did, z)] - loss_cache[did]
        km_total += km
        cov.apply(did, old, -1)
        cov.apply(did, z, +1)
        home[did] = z
        moves[did] = inputs.zones[z]
        steps += 1
        changed = {old, z}
        add_cache = {k: v for k, v in add_cache.items() if k[1] not in changed}
        loss_cache = {d: v for d, v in loss_cache.items() if home[d] not in changed}
    return Plan(moves, gain_total, km_total, steps)


def threshold_rule(inputs: PlanInputs, *, theta: float, rho_km: float, max_km: float) -> Plan:
    cov = _Coverage(inputs)
    home = {d.did: home_zone(d.lat, d.lon, inputs.zones, rho_km) for d in inputs.drivers}
    for did, z in home.items():
        cov.apply(did, z, +1)
    targets = _targets(inputs)
    moves, gain, km_total = {}, 0.0, 0.0
    for d in inputs.drivers:
        loss = cov.delta_remove(d.did, home[d.did])
        options = []
        for z in targets:
            km = reta_km(d.lat, d.lon, *inputs.zones[z]) * inputs.road_factor
            if z == home[d.did] or km > max_km or km <= 1e-9:
                continue
            g = cov.delta_add(d.did, z) - loss
            options.append((g / km, z, g, km))
        if options:
            ratio, z, g, km = max(options, key=lambda o: (o[0], o[1]))
            if ratio >= theta and g > 0:
                moves[d.did] = inputs.zones[z]
                gain += g
                km_total += km
    return Plan(moves, gain, km_total, len(moves))


def proportional(inputs: PlanInputs, *, max_km: float) -> Plan:
    expected = defaultdict(float)
    for (h, z), v in inputs.demand.items():
        if z in inputs.zones:
            expected[z] += v
    capacity = inputs.kappa * len(inputs.hours)
    slots = [z for z, n in target_slots(dict(expected), capacity, len(inputs.drivers)).items() for _ in range(n)]
    pairs = sorted((reta_km(d.lat, d.lon, *inputs.zones[z]) * inputs.road_factor, d.did, i)
                   for d in inputs.drivers for i, z in enumerate(slots))
    used_d, used_s, moves, km_total = set(), set(), {}, 0.0
    for km, did, i in pairs:
        if did in used_d or i in used_s or km > max_km:
            continue
        used_d.add(did)
        used_s.add(i)
        if km > 1e-9:
            moves[did] = inputs.zones[slots[i]]
            km_total += km
    return Plan(moves, 0.0, km_total, len(moves))
