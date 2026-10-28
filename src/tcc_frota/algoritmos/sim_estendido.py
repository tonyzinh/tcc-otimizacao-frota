"""Simulador estendido para os experimentos fora da tabela principal (5.9 intradiário e 5.11 despacho D+0).

Cópia de `tcc_frota.v2.sim.simulate` (sem o rastro de visualização) com três ganchos opcionais:

- `dispatch="lote"`: em vez do motorista livre mais próximo no instante do pedido, a cada `batch_s`
  segundos os pedidos em espera e os motoristas livres elegíveis são casados por atribuição de custo
  mínimo (km de busca, `linear_sum_assignment`); motorista que fica livre espera o próximo lote.
- `dispatch_radius_km`: raio de despacho diferente do calibrado (variante que pode recusar corridas).
- `epochs` + `epoch_planner`: em cada instante de replanejamento, o planejador recebe os motoristas
  livres (e os ocupados, com a hora e a posição em que ficarão livres) e devolve reposicionamentos
  imediatos; o km entra no total e o motorista fica ocupado durante o trajeto (cenário intradiário).

Com os valores padrão, o resultado é idêntico ao do simulador da v2 (teste
`tests/unit/test_algoritmos_sim_estendido.py`). O simulador da v2 não foi alterado.
"""

from __future__ import annotations

import heapq

import numpy as np
from scipy.optimize import linear_sum_assignment

from tcc_frota.v2.sim import SimDriver, SimParams, SimRequest, SimResult, _merge, reta_km, signature


def simulate_ext(
    requests: list[SimRequest],
    drivers: list[SimDriver],
    params: SimParams,
    window: tuple[float, float],
    moves: dict[str, tuple[float, float]] | None = None,
    tail_s: float = 3 * 3600,
    max_move_km: float = float("inf"),
    move_mode: str = "inicio_turno",
    move_origins: dict[str, tuple[float, float]] | None = None,
    *,
    dispatch: str = "proximo",
    batch_s: float = 60.0,
    dispatch_radius_km: float | None = None,
    epochs: tuple[float, ...] = (),
    epoch_planner=None,
) -> SimResult:
    if move_mode not in ("inicio_turno", "fim_do_dia") or dispatch not in ("proximo", "lote"):
        raise ValueError("modo inválido")
    radius = params.radius_km if dispatch_radius_km is None else dispatch_radius_km
    move_origins = move_origins or {}
    if len({r.rid for r in requests}) != len(requests) or len({d.did for d in drivers}) != len(drivers):
        raise ValueError("pedidos ou motoristas duplicados")
    moves = dict(moves or {})
    unknown = set(moves) - {d.did for d in drivers}
    w0, w1 = window
    res = SimResult(signature(requests, drivers, params, window), moves_planned=len(moves))
    for d in unknown:
        moves.pop(d)
        res.move_outcomes[d] = "absent"
    horizon = w1 + tail_s
    online = {d.did: False for d in drivers}
    busy_until = {d.did: None for d in drivers}
    busy_target: dict[str, tuple[float, float]] = {}
    pos: dict[str, tuple[float, float] | None] = {d.did: None for d in drivers}
    commits = {d.did: _merge(d.commitments) for d in drivers}
    next_commit = {d.did: 0 for d in drivers}
    pending_move = dict(moves)
    first_start = {d.did: min((x[0] for x in d.sessions), default=float("inf")) for d in drivers}
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
    if dispatch == "lote":
        push(w0, 6, "batch", None)
    for t in epochs:
        if w0 <= t < w1:
            push(t, 7, "epoch", None)

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
        cancel = params.post_accept_cancel and r.post_accept_cancel
        end_pos = (r.lat, r.lon) if cancel else (r.dlat, r.dlon)
        busy_target[did] = end_pos
        res.jobs.append((did, t, t + total, "corrida"))
        push(t + total, 3, "job_end", (did, end_pos))

    def eligible(did: str, r: SimRequest, t: float) -> float | None:
        if not online[did] or busy_until[did] is not None or pos[did] is None:
            return None
        d = reta_km(pos[did][0], pos[did][1], r.lat, r.lon)
        if d > radius:
            return None
        _, total = job_seconds(did, r)
        if commit_blocks(did, t, t + total):
            return None
        return d

    def travel(did: str, t: float, target: tuple[float, float], km: float, kind: str) -> None:
        end = t + 3600 * km / params.speed_kmh
        res.reposition_km += km
        res.moves_executed += 1
        busy_until[did] = end
        busy_target[did] = target
        res.jobs.append((did, t, end, kind))
        push(end, 3, "job_end", (did, target))

    def try_move(did: str, t: float) -> bool:
        if did not in pending_move:
            return False
        lat, lon = pending_move.pop(did)
        if move_mode == "fim_do_dia":
            res.move_outcomes[did] = "busy"
            return False
        if t >= w1:
            res.move_outcomes[did] = "not_free_in_window"
            return False
        km = reta_km(pos[did][0], pos[did][1], lat, lon) * params.road_factor
        end = t + 3600 * km / params.speed_kmh
        if km <= 1e-9 or km > max_move_km + 1e-9 or commit_blocks(did, t, end):
            res.move_outcomes[did] = "already_there" if km <= 1e-9 else "limit" if km > max_move_km + 1e-9 else "busy"
            return False
        res.move_outcomes[did] = "executed"
        res.move_origins_used[did] = pos[did]
        travel(did, t, (lat, lon), km, "reposicionamento")
        return True

    def become_free(did: str, t: float) -> None:
        busy_until[did] = None
        if not online[did] or pos[did] is None:
            return
        if try_move(did, t):
            return
        if dispatch == "lote":
            return
        best = None
        for rid in sorted(waiting):
            r = waiting[rid]
            if eligible(did, r, t) is not None:
                best = r
                break
        if best is not None:
            del waiting[best.rid]
            assign(did, best, t)

    def run_batch(t: float) -> None:
        reqs = sorted(waiting.values(), key=lambda r: r.rid)
        free = sorted(did for did in online if online[did] and busy_until[did] is None and pos[did] is not None)
        if reqs and free:
            cost = np.full((len(free), len(reqs)), 1e9)
            for i, did in enumerate(free):
                for j, r in enumerate(reqs):
                    if eligible(did, r, t) is not None:
                        cost[i, j] = reta_km(pos[did][0], pos[did][1], r.lat, r.lon)
            rows, cols = linear_sum_assignment(cost)
            for i, j in sorted(zip(rows, cols), key=lambda ij: reqs[ij[1]].rid):
                if cost[i, j] < 1e9:
                    del waiting[reqs[j].rid]
                    assign(free[i], reqs[j], t)
        if t + batch_s < horizon:
            push(t + batch_s, 6, "batch", None)

    def run_epoch(t: float) -> None:
        idle = {
            did: pos[did] for did in online if online[did] and busy_until[did] is None and pos[did] is not None and did not in pending_move
        }
        busy = {did: (busy_until[did], busy_target.get(did, pos[did])) for did in online if online[did] and busy_until[did] is not None}
        plan = epoch_planner(t, idle, busy) if epoch_planner else {}
        for did, target in sorted(plan.items()):
            if did not in idle:
                continue
            res.moves_planned += 1
            km = reta_km(idle[did][0], idle[did][1], target[0], target[1]) * params.road_factor
            end = t + 3600 * km / params.speed_kmh
            if km <= 1e-9 or km > max_move_km + 1e-9 or commit_blocks(did, t, end):
                continue
            travel(did, t, target, km, "reposicionamento_intradiario")

    while events:
        t, _, _, kind, data = heapq.heappop(events)
        if kind == "sess_start":
            did, lat, lon = data
            online[did] = True
            if busy_until[did] is None:
                if lat is not None:
                    pos[did] = (lat, lon)
                if move_mode == "fim_do_dia" and did in pending_move:
                    target = pending_move.pop(did)
                    origin = move_origins.get(did) or pos[did]
                    km = reta_km(origin[0], origin[1], target[0], target[1]) * params.road_factor
                    if first_start[did] < w0 - 1800:
                        res.move_outcomes[did] = "early"
                    elif km <= 1e-9:
                        res.move_outcomes[did] = "already_there"
                    elif km > max_move_km + 1e-9:
                        res.move_outcomes[did] = "limit"
                    if first_start[did] >= w0 - 1800 and 1e-9 < km <= max_move_km + 1e-9:
                        res.move_outcomes[did] = "executed"
                        res.move_origins_used[did] = origin
                        res.reposition_km += km
                        res.moves_executed += 1
                        res.jobs.append((did, t, t, "reposicionamento_fim_do_dia"))
                        pos[did] = target
                become_free(did, t)
        elif kind == "sess_end":
            online[data] = False
        elif kind == "commit_start":
            did, i = data
            s, e, lat, lon = commits[did][i]
            if pending_move.pop(did, None) is not None:
                res.move_outcomes[did] = "busy"
            if busy_until[did] is not None:
                raise AssertionError("compromisso sobreposto a tarefa simulada (RN017)")
            next_commit[did] = i
            busy_until[did] = e
            busy_target[did] = (lat, lon)
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
            if dispatch == "proximo":
                options = [(d, did) for did in online if (d := eligible(did, r, t)) is not None]
                if options:
                    _, did = min(options)
                    assign(did, r, t)
                    continue
            waiting[r.rid] = r
            patience = params.patience_s if r.patience_s is None else min(params.patience_s, r.patience_s)
            push(t + patience, 5, "deadline", r.rid)
        elif kind == "deadline":
            waiting.pop(data, None)
        elif kind == "batch":
            run_batch(t)
        elif kind == "epoch":
            run_epoch(t)
    for did in pending_move:
        res.move_outcomes[did] = "not_free_in_window"
    return res
