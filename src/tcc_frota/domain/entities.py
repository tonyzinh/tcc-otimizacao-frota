"""Simulador de eventos v2 (Fase 4), mantido ao lado de `simulation/engine.py` (legado).

Diferenças em relação ao legado: demanda inclui não atendidas; fila com paciência; raio máximo de
despacho; fator rua/reta e velocidade como parâmetros calibrados; compromissos externos (corridas
reais fora do universo simulado) bloqueiam o motorista; reposicionamento preventivo é executado na
primeira vez que o motorista fica livre na janela e seu KM entra no total (RN011/RN031); nenhum
motorista cumpre dois intervalos ocupados ao mesmo tempo (RN017). Tempos em segundos desde a
meia-noite local do dia simulado; distâncias por rua estimadas = Haversine × fator (nunca odômetro).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from math import asin, cos, radians, sin, sqrt


def reta_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, l1, p2, l2 = map(radians, (lat1, lon1, lat2, lon2))
    h = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin((l2 - l1) / 2) ** 2
    return 6371.0088 * 2 * asin(min(1.0, sqrt(h)))


@dataclass(frozen=True)
class SimParams:
    radius_km: float  # raio máximo de despacho, em linha reta
    speed_kmh: float  # velocidade efetiva sobre a distância por rua estimada
    road_factor: float  # distância por rua / linha reta
    patience_s: float  # paciência máxima na fila
    post_accept_cancel: bool = False  # sensibilidade: canceladas pós-aceite não viram viagem

    def __post_init__(self) -> None:
        if min(self.radius_km, self.speed_kmh, self.road_factor) <= 0 or self.patience_s < 0:
            raise ValueError("parâmetros do simulador inválidos")


@dataclass(frozen=True)
class SimRequest:
    rid: int
    t: float
    lat: float
    lon: float
    dlat: float
    dlon: float
    trip_s: float
    patience_s: float | None = None  # desistência observada antes do aceite, se houver
    post_accept_cancel: bool = False
    hour: int = 0
    zone: str = ""


@dataclass(frozen=True)
class SimDriver:
    did: str
    sessions: tuple[tuple[float, float, float, float], ...]  # (início, fim, lat, lon)
    commitments: tuple[tuple[float, float, float, float], ...] = ()  # (início, fim, lat_fim, lon_fim)


@dataclass
class SimResult:
    signature: str
    n_requests: int = 0
    served: int = 0
    pickup_km: float = 0.0
    reposition_km: float = 0.0
    moves_planned: int = 0
    moves_executed: int = 0
    wait_s: list[float] = field(default_factory=list)
    served_ids: set[int] = field(default_factory=set)
    served_by_hour: dict[int, int] = field(default_factory=dict)
    requests_by_hour: dict[int, int] = field(default_factory=dict)
    pickup_km_by_hour: dict[int, float] = field(default_factory=dict)
    jobs: list[tuple[str, float, float, str]] = field(default_factory=list)  # (motorista, início, fim, tipo)
    # Desfecho de cada recomendação: executed, absent, busy, limit, early, already_there, not_free_in_window.
    move_outcomes: dict[str, str] = field(default_factory=dict)
    move_origins_used: dict[str, tuple[float, float]] = field(default_factory=dict)
    # Compromissos com deslocamento explícito (só com `commit_origins`): km de aproximação à origem do compromisso (componente
    # SEPARADO do KM vazio comparado) e um registro por compromisso, com a causa de qualquer folga insuficiente.
    commit_approach_km: float = 0.0
    commit_events: list[dict] = field(default_factory=list)

    @property
    def empty_km(self) -> float:
        return self.pickup_km + self.reposition_km


def signature(requests: list[SimRequest], drivers: list[SimDriver], params: SimParams, window: tuple[float, float]) -> str:
    """SHA-256 das entradas do mundo (sem o plano): igual nos cenários comparados (RN028)."""
    payload = json.dumps(
        {
            "requests": [asdict(r) for r in sorted(requests, key=lambda r: r.rid)],
            "drivers": [asdict(d) for d in sorted(drivers, key=lambda d: d.did)],
            "params": asdict(params),
            "window": window,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()
