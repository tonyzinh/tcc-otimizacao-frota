"""Interface única de planejador D+1 para a bateria de algoritmos.

Um planejador recebe o contexto do corte (o que se sabe no fim de D, conforme o regime de
informação) e devolve os reposicionamentos: `{motorista: (lat, lng, km)}`, com km por rua estimado
(reta × fator rua/reta calibrado). Nada de D+1 entra no contexto, exceto a escala no regime B
(premissa do regime). Os pseudodias de `scenarios` são dias **anteriores** a D, usados por
planejadores que avaliam planos no simulador; o dia D+1 real só é simulado pelo avaliador externo.

Os adaptadores `GulosoMarginal`, `Proporcional` e `RegraLimiar` chamam as funções de
`tcc_frota.v2.policy` sem alterá-las (teste de regressão em `tests/unit/test_algoritmos_base.py`).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

from tcc_frota.v2.policy import PlanInputs, marginal_greedy, proportional, threshold_rule
from tcc_frota.v2.sim import SimDriver, SimParams, SimRequest, reta_km

Moves = dict[str, tuple[float, float, float]]   # motorista -> (lat, lng, km por rua estimado)


@dataclass(frozen=True)
class Scenario:
    """Pseudodia histórico: pedidos de um dia anterior a D, com horários na mesma janela."""

    day: date
    requests: tuple[SimRequest, ...]


@dataclass(frozen=True)
class PlanContext:
    inputs: PlanInputs                    # frota do regime, zonas, demanda prevista, κ, fator rua/reta
    target: date                          # D+1
    window: tuple[int, int]               # horas locais [início, fim)
    regime: str                           # "A" ou "B" (C só diagnóstico)
    sim: SimParams                        # simulador calibrado do período (conhecido no corte)
    move_mode: str                        # execução do regime: "inicio_turno" ou "fim_do_dia"
    scenarios: tuple[Scenario, ...] = ()  # dias anteriores a D, mesmo dia da semana
    seed: int = 0
    extras: dict = field(default_factory=dict)   # agregados históricos anteriores ao corte (opcional)

    @property
    def window_s(self) -> tuple[float, float]:
        return self.window[0] * 3600.0, self.window[1] * 3600.0


class Planner(ABC):
    """Contrato: `plan(contexto) -> {motorista: (lat, lng, km)}`.

    `max_km` é o salto máximo; o avaliador recusa na execução qualquer deslocamento real maior
    (não adesão). `stochastic` indica se a semente muda o plano. `info` guarda diagnósticos da última
    chamada (status do solver, objetivo do modelo, avaliações), sem dados pessoais."""

    family: str = ""
    stochastic: bool = False

    def __init__(self, max_km: float):
        if max_km <= 0:
            raise ValueError("max_km deve ser positivo")
        self.max_km = max_km
        self.info: dict = {}

    @property
    def params(self) -> dict:
        return {"max_km": self.max_km}

    @abstractmethod
    def plan(self, ctx: PlanContext) -> Moves:
        ...


def with_km(inputs: PlanInputs, moves: dict[str, tuple[float, float]]) -> Moves:
    """Acrescenta o km por rua estimado (mesma regra dos planejadores) a cada movimento."""
    by = {d.did: d for d in inputs.drivers}
    return {did: (lat, lon, reta_km(by[did].lat, by[did].lon, lat, lon) * inputs.road_factor)
            for did, (lat, lon) in moves.items()}


def latlon(moves: Moves) -> dict[str, tuple[float, float]]:
    return {did: (lat, lon) for did, (lat, lon, _) in moves.items()}


def scenario_drivers(inputs: PlanInputs) -> list[SimDriver]:
    """Frota que o planejador enxerga, como motoristas do simulador: uma sessão no horário previsto."""
    return [SimDriver(d.did, ((d.start_h * 3600.0, d.end_h * 3600.0, d.lat, d.lon),)) for d in inputs.drivers]


# ------------------------------------------------------------------ adaptadores dos planejadores existentes
class GulosoMarginal(Planner):
    """Guloso de valor marginal do artigo: a cada passo, maior ΔV − α·d; para quando o saldo ≤ 0."""

    family = "guloso_marginal"

    def __init__(self, alpha: float, rho_km: float, max_km: float):
        super().__init__(max_km)
        self.alpha, self.rho_km = alpha, rho_km

    @property
    def params(self) -> dict:
        return {"alpha": self.alpha, "rho_km": self.rho_km, "max_km": self.max_km}

    def plan(self, ctx: PlanContext) -> Moves:
        p = marginal_greedy(ctx.inputs, alpha=self.alpha, rho_km=self.rho_km, max_km=self.max_km)
        self.info = {"ganho_modelo": p.expected_gain, "km_modelo": p.planned_km, "passos": p.steps}
        return with_km(ctx.inputs, p.moves)


class Proporcional(Planner):
    """Vagas proporcionais à demanda prevista, preenchidas pelo par motorista–vaga mais próximo."""

    family = "proporcional"

    def plan(self, ctx: PlanContext) -> Moves:
        p = proportional(ctx.inputs, max_km=self.max_km)
        self.info = {"km_modelo": p.planned_km}
        return with_km(ctx.inputs, p.moves)


class RegraLimiar(Planner):
    """Cada motorista, isoladamente, vai à zona de maior ganho por km se ganho/km ≥ θ."""

    family = "regra_limiar"

    def __init__(self, theta: float, rho_km: float, max_km: float):
        super().__init__(max_km)
        self.theta, self.rho_km = theta, rho_km

    @property
    def params(self) -> dict:
        return {"theta": self.theta, "rho_km": self.rho_km, "max_km": self.max_km}

    def plan(self, ctx: PlanContext) -> Moves:
        p = threshold_rule(ctx.inputs, theta=self.theta, rho_km=self.rho_km, max_km=self.max_km)
        self.info = {"ganho_modelo": p.expected_gain, "km_modelo": p.planned_km}
        return with_km(ctx.inputs, p.moves)


class SemReposicionamento(Planner):
    """Plano vazio (baseline como planejador, útil para conferências)."""

    family = "nenhum"

    def __init__(self, max_km: float = 1.0):
        super().__init__(max_km)

    def plan(self, ctx: PlanContext) -> Moves:
        self.info = {}
        return {}


@dataclass
class PlannerSpec:
    """Configuração registrável: família, nome do cenário e parâmetros do construtor."""

    family: str
    name: str
    params: dict = field(default_factory=dict)
