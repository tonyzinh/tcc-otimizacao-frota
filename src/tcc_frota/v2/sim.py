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
import heapq
import json
from dataclasses import asdict, dataclass, field
from math import asin, cos, radians, sin, sqrt


def reta_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, l1, p2, l2 = map(radians, (lat1, lon1, lat2, lon2))
    h = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin((l2 - l1) / 2) ** 2
    return 6371.0088 * 2 * asin(min(1.0, sqrt(h)))


@dataclass(frozen=True)
class SimParams:
    radius_km: float          # raio máximo de despacho, em linha reta
    speed_kmh: float          # velocidade efetiva sobre a distância por rua estimada
    road_factor: float        # distância por rua / linha reta
    patience_s: float         # paciência máxima na fila
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
    patience_s: float | None = None      # desistência observada antes do aceite, se houver
    post_accept_cancel: bool = False
    hour: int = 0
    zone: str = ""


@dataclass(frozen=True)
class SimDriver:
    did: str
    sessions: tuple[tuple[float, float, float, float], ...]       # (início, fim, lat, lon)
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

    @property
    def empty_km(self) -> float:
        return self.pickup_km + self.reposition_km


def signature(requests: list[SimRequest], drivers: list[SimDriver], params: SimParams, window: tuple[float, float]) -> str:
    """SHA-256 das entradas do mundo (sem o plano): igual nos cenários comparados (RN028)."""
    payload = json.dumps({
        "requests": [asdict(r) for r in sorted(requests, key=lambda r: r.rid)],
        "drivers": [asdict(d) for d in sorted(drivers, key=lambda d: d.did)],
        "params": asdict(params), "window": window,
    }, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def _merge(intervals) -> list[tuple[float, float, float, float]]:
    out: list[list[float]] = []
    for s, e, lat, lon in sorted(intervals):
        if out and s < out[-1][1]:
            if e > out[-1][1]:
                out[-1][1:] = [e, lat, lon]
        else:
            out.append([s, e, lat, lon])
    return [tuple(x) for x in out]


def simulate(requests: list[SimRequest], drivers: list[SimDriver], params: SimParams,
             window: tuple[float, float], moves: dict[str, tuple[float, float]] | None = None,
             tail_s: float = 3 * 3600, max_move_km: float = float("inf")) -> SimResult:
    """Replay de um dia. Uma recomendação só é executada na primeira disponibilidade do motorista
    na janela e se o deslocamento real (por rua estimado) respeitar `max_move_km`; caso contrário
    conta como não executada (não adesão)."""
    if len({r.rid for r in requests}) != len(requests) or len({d.did for d in drivers}) != len(drivers):
        raise ValueError("pedidos ou motoristas duplicados")
    moves = dict(moves or {})
    unknown = set(moves) - {d.did for d in drivers}
    w0, w1 = window
    res = SimResult(signature(requests, drivers, params, window), moves_planned=len(moves))
    res.moves_planned = len(moves)
    for d in unknown:          # recomendação para motorista que não trabalha: não executada
        moves.pop(d)
    horizon = w1 + tail_s
    online = {d.did: False for d in drivers}
    busy_until = {d.did: None for d in drivers}   # None = livre
    pos: dict[str, tuple[float, float] | None] = {d.did: None for d in drivers}
    commits = {d.did: _merge(d.commitments) for d in drivers}
    next_commit = {d.did: 0 for d in drivers}
    pending_move = dict(moves)
    waiting: dict[int, SimRequest] = {}
    events: list = []
    seq = 0

    def push(t: float, prio: int, kind: str, data) -> None:
        nonlocal seq
        seq += 1
        heapq.heappush(events, (t, prio, seq, kind, data))

    for d in drivers:
        for s, e, lat, lon in d.sessions:
            if e > w0 and s < horizon:
                push(max(s, w0), 1, "sess_start", (d.did, lat, lon))
                push(e, 0, "sess_end", d.did)
        for i, (s, e, lat, lon) in enumerate(commits[d.did]):
            if e > w0 and s < horizon:
                push(max(s, w0), 2, "commit_start", (d.did, i))
    for r in requests:
        if w0 <= r.t < w1:
            res.n_requests += 1
            res.requests_by_hour[r.hour] = res.requests_by_hour.get(r.hour, 0) + 1
            push(r.t, 4, "request", r)

    def commit_blocks(did: str, start: float, end: float) -> bool:
        cs = commits[did]
        k = next_commit[did]
        while k < len(cs) and cs[k][1] <= start:
            k += 1
        return k < len(cs) and cs[k][0] < end

    def job_seconds(did: str, r: SimRequest) -> tuple[float, float]:
        km = reta_km(pos[did][0], pos[did][1], r.lat, r.lon) * params.road_factor
        pickup = 3600 * km / params.speed_kmh
        cancel = params.post_accept_cancel and r.post_accept_cancel
        return km, pickup + (0.0 if cancel else r.trip_s)

    def assign(did: str, r: SimRequest, t: float) -> None:
        km, total = job_seconds(did, r)
        pickup_s = 3600 * km / params.speed_kmh
        res.served += 1
        res.served_ids.add(r.rid)
        res.pickup_km += km
        res.wait_s.append(t - r.t + pickup_s)
        res.served_by_hour[r.hour] = res.served_by_hour.get(r.hour, 0) + 1
        res.pickup_km_by_hour[r.hour] = res.pickup_km_by_hour.get(r.hour, 0.0) + km
        busy_until[did] = t + total
        res.jobs.append((did, t, t + total, "corrida"))
        cancel = params.post_accept_cancel and r.post_accept_cancel
        push(t + total, 3, "job_end", (did, (r.lat, r.lon) if cancel else (r.dlat, r.dlon)))

    def eligible(did: str, r: SimRequest, t: float) -> float | None:
        if not online[did] or busy_until[did] is not None or pos[did] is None:
            return None
        d = reta_km(pos[did][0], pos[did][1], r.lat, r.lon)
        if d > params.radius_km:
            return None
        _, total = job_seconds(did, r)
        if commit_blocks(did, t, t + total):
            return None
        return d

    def try_move(did: str, t: float) -> bool:
        """Executa o reposicionamento pendente; devolve True se o motorista ficou ocupado."""
        if did not in pending_move:
            return False
        lat, lon = pending_move.pop(did)
        if t >= w1:
            return False
        km = reta_km(pos[did][0], pos[did][1], lat, lon) * params.road_factor
        end = t + 3600 * km / params.speed_kmh
        if km <= 1e-9 or km > max_move_km + 1e-9 or commit_blocks(did, t, end):
            return False
        res.reposition_km += km
        res.moves_executed += 1
        busy_until[did] = end
        res.jobs.append((did, t, end, "reposicionamento"))
        push(end, 3, "job_end", (did, (lat, lon)))
        return True

    def become_free(did: str, t: float) -> None:
        busy_until[did] = None
        if not online[did] or pos[did] is None:
            return
        if try_move(did, t):
            return
        best = None
        for rid in sorted(waiting):          # FIFO: pedido mais antigo primeiro
            r = waiting[rid]
            if eligible(did, r, t) is not None:
                best = r
                break
        if best is not None:
            del waiting[best.rid]
            assign(did, best, t)

    while events:
        t, _, _, kind, data = heapq.heappop(events)
        if kind == "sess_start":
            did, lat, lon = data
            online[did] = True
            if busy_until[did] is None:
                if lat is not None:
                    pos[did] = (lat, lon)
                become_free(did, t)
        elif kind == "sess_end":
            online[data] = False
        elif kind == "commit_start":
            did, i = data
            s, e, lat, lon = commits[did][i]
            pending_move.pop(did, None)   # ocupado antes da primeira disponibilidade: não executa
            if busy_until[did] is not None:
                raise AssertionError("compromisso sobreposto a tarefa simulada (RN017)")
            next_commit[did] = i
            busy_until[did] = e
            res.jobs.append((did, max(s, w0), e, "compromisso"))
            push(e, 3, "job_end", (did, (lat, lon)))
        elif kind == "job_end":
            did, end_pos = data
            if busy_until[did] is None or abs(busy_until[did] - t) > 1e-6:
                continue
            pos[did] = end_pos
            k = next_commit[did]
            while k < len(commits[did]) and commits[did][k][1] <= t:
                k += 1
            next_commit[did] = k
            become_free(did, t)
        elif kind == "request":
            r = data
            options = [(d, did) for did in online if (d := eligible(did, r, t)) is not None]
            if options:
                _, did = min(options)
                assign(did, r, t)
            else:
                waiting[r.rid] = r
                patience = params.patience_s if r.patience_s is None else min(params.patience_s, r.patience_s)
                push(t + patience, 5, "deadline", r.rid)
        elif kind == "deadline":
            waiting.pop(data, None)
    return res
