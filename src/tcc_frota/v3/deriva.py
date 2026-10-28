"""Políticas de deriva dos veículos livres (baselines B1–B3 da Fase 4) e configuração do reativo (B4).

Um veículo livre tem um estado de deriva que dá a posição e o KM percorrido em qualquer instante t >= t0 (cálculo preguiçoso:
nada é simulado até o veículo ser despachado, reposicionado, comprometido ou encerrar a sessão). O veículo continua despachável
na posição interpolada. O KM de deriva entra no KM vazio dos dois braços (pré-registro §8, Fase 4).
"""

from __future__ import annotations

import math
import random
import zlib
from dataclasses import dataclass, field

from tcc_frota.v2.sim import reta_km

LatLon = tuple[float, float]


def _lerp(p: LatLon, q: LatLon, f: float) -> LatLon:
    return p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f


@dataclass
class GoTo:
    """Segue em linha reta até `target` na velocidade efetiva e para; km por rua = reta × fator."""

    t0: float
    p0: LatLon
    target: LatLon
    speed_kmh: float
    road_factor: float

    def position(self, t: float) -> tuple[LatLon, float]:
        total = reta_km(*self.p0, *self.target) * self.road_factor
        if total <= 1e-12:
            return self.p0, 0.0
        walked = min(total, self.speed_kmh * max(0.0, t - self.t0) / 3600.0)
        return _lerp(self.p0, self.target, walked / total), walked


@dataclass
class Cruise:
    """Passeio aleatório: pontos uniformes num quadrado de lado `side_km` centrado em `anchor`, percorridos em sequência."""

    t0: float
    p0: LatLon
    anchor: LatLon
    side_km: float
    speed_kmh: float
    road_factor: float
    seed: int
    _legs: list = field(default_factory=list)  # (t_fim, p_fim, km_acumulado)
    _rng: random.Random | None = None

    def _extend(self, t: float) -> None:
        if self._rng is None:
            self._rng = random.Random(self.seed)
            self._legs.append((self.t0, self.p0, 0.0))
        half_lat = self.side_km / 2 / 111.19
        half_lon = half_lat / max(0.2, abs(math.cos(math.radians(self.anchor[0]))))
        while self._legs[-1][0] < t:
            t_prev, p_prev, km_prev = self._legs[-1]
            q = (self.anchor[0] + self._rng.uniform(-half_lat, half_lat), self.anchor[1] + self._rng.uniform(-half_lon, half_lon))
            km = reta_km(*p_prev, *q) * self.road_factor
            dur = max(1.0, 3600.0 * km / self.speed_kmh)
            self._legs.append((t_prev + dur, q, km_prev + km))

    def position(self, t: float) -> tuple[LatLon, float]:
        t = max(t, self.t0)
        self._extend(t)
        for i in range(1, len(self._legs)):
            t_end, q, km_end = self._legs[i]
            if t <= t_end:
                t_prev, p_prev, km_prev = self._legs[i - 1]
                f = (t - t_prev) / max(1e-9, t_end - t_prev)
                return _lerp(p_prev, q, f), km_prev + (km_end - km_prev) * f
        return self._legs[-1][1], self._legs[-1][2]


@dataclass
class Observed:
    """Reproduz o deslocamento observado do próprio motorista enquanto livre (fotos de 10 min, interpolação linear).

    `pieces`: (ta, tb, dlat, dlon, km) por par de fotos consecutivas ambas livres; km = reta × fator. A resolução temporal
    subestima o movimento real (limitação declarada)."""

    t0: float
    p0: LatLon
    pieces: tuple

    def position(self, t: float) -> tuple[LatLon, float]:
        lat, lon, km = self.p0[0], self.p0[1], 0.0
        for ta, tb, dlat, dlon, piece_km in self.pieces:
            lo, hi = max(ta, self.t0), min(tb, t)
            if hi <= lo:
                continue
            f = (hi - lo) / (tb - ta)
            lat += dlat * f
            lon += dlon * f
            km += piece_km * f
        return (lat, lon), km


class DriftPolicy:
    name = "B0_estacionario"

    def start(self, did: str, t: float, pos: LatLon, anchor: LatLon, speed_kmh: float, road_factor: float):
        return None


class ReturnHome(DriftPolicy):
    """B1: ao ficar livre, volta à posição de início da sessão (no braço do plano, o alvo reposicionado)."""

    name = "B1_retorno_origem"

    def start(self, did, t, pos, anchor, speed_kmh, road_factor):
        return GoTo(t, pos, anchor, speed_kmh, road_factor)


class LocalCruise(DriftPolicy):
    """B3: passeio aleatório numa vizinhança fixa (padrão 2×2 km) em torno da posição de início da sessão."""

    name = "B3_cruzeiro_local"

    def __init__(self, side_km: float = 2.0, seed: int = 20261028):
        self.side_km, self.seed = side_km, seed

    def start(self, did, t, pos, anchor, speed_kmh, road_factor):
        seed = zlib.crc32(f"{self.seed}|{did}|{int(t)}".encode())
        return Cruise(t, pos, anchor, self.side_km, speed_kmh, road_factor, seed)


class ObservedTracks(DriftPolicy):
    """B2: movimento observado dos livres (`tracks[did]` = peças de `observed_pieces`)."""

    name = "B2_movimento_observado"

    def __init__(self, tracks: dict[str, tuple]):
        self.tracks = tracks

    def start(self, did, t, pos, anchor, speed_kmh, road_factor):
        pieces = self.tracks.get(did)
        return Observed(t, pos, pieces) if pieces else None


def observed_pieces(
    snaps: list[tuple[float, float, float, int]], road_factor: float, max_gap_s: float = 720.0, max_speed_kmh: float = 80.0
) -> tuple:
    """Peças de movimento livre a partir de fotos ordenadas `(t, lat, lon, estado)`; estado 1 = ONLINE (livre).

    Descarta pares com intervalo > `max_gap_s` ou velocidade reta implausível (> `max_speed_kmh`, salto de GPS)."""
    out = []
    for (ta, la, loa, ea), (tb, lb, lob, eb) in zip(snaps, snaps[1:]):
        if ea != 1 or eb != 1 or tb <= ta or tb - ta > max_gap_s:
            continue
        reta = reta_km(la, loa, lb, lob)
        if reta / ((tb - ta) / 3600.0) > max_speed_kmh:
            continue
        out.append((ta, tb, lb - la, lob - loa, reta * road_factor))
    return tuple(out)


@dataclass(frozen=True)
class ReactiveConfig:
    """B4: a cada `tick_s`, livres são alocados (alocação ótima por distância) às origens de pedidos não atendidos nos últimos
    `lookback_s`, desde que a distância em linha reta seja <= `max_km`. Só usa o passado (pedidos já perdidos)."""

    tick_s: float = 300.0
    lookback_s: float = 900.0
    max_km: float = 3.0
