"""Simulador v3: cópia de `tcc_frota.v2.sim.simulate` com correções de contabilização opcionais (m1, m2).

Com `fix_m1=False` e `fix_m2=False` reproduz a v1 bit a bit (teste de regressão). Ver docs/V2_CONTABILIZACAO.md.

- m1: reposicionamento (modo `inicio_turno`) que terminaria depois do fim da sessão vigente não é executado
  (desfecho `excede_sessao`); na v1 o KM era contado mesmo com o motorista já offline.
- m2: assimetria de posição noturna (modo `fim_do_dia`). Duas operacionalizações:
  (a) `start_at_origin` (primária, desvio D10): os dois braços começam a sessão na última posição de D, como o regime B
  pressupõe ("motoristas dormem onde largam"); o plano paga origem → alvo e o baseline não paga nada.
  (b) `fix_m2` ("pagar nos dois", sensibilidade): ver abaixo. O placebo mostrou que (b) cria economia espúria.
  Descrição de (b): Na v1 o plano paga o deslocamento da última posição de D
  até a zona-alvo, mas o baseline não paga o deslocamento natural da última posição de D até a posição observada no
  início da sessão. Com `fix_m2`, os dois braços pagam esse trecho: `overnight_km` = alvo (se moveu) ou posição
  observada (se não moveu), e `empty_km_sim` = busca + `overnight_km` (+ reposicionamento em `inicio_turno`).
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass

from tcc_frota.v2.sim import SimDriver, SimParams, SimRequest, SimResult, _merge, reta_km, signature
from tcc_frota.v3.deriva import DriftPolicy, GoTo, ReactiveConfig


@dataclass
class SimResult3(SimResult):
    overnight_km: float = 0.0              # trecho noturno pago pelos dois braços (só com fix_m2)
    overnight_drivers: int = 0
    in_service_repos_km: float = 0.0       # reposicionamento executado em horário de serviço (modo inicio_turno)
    drift_km: float = 0.0                  # KM de movimento dos livres (políticas B1–B4); 0 sem política
    m2: bool = False

    @property
    def empty_km_sim(self) -> float:
        """KM vazio: v1 (`empty_km`) sem fix_m2; com fix_m2, busca + trecho noturno + reposicionamento em serviço."""
        if not self.m2:
            return self.empty_km + self.drift_km
        return self.pickup_km + self.overnight_km + self.in_service_repos_km + self.drift_km

    @property
    def empty_km_v1(self) -> float:
        """Contabilização da v1 acrescida do KM de deriva (zero sem política de baseline)."""
        return self.empty_km + self.drift_km


def simulate3(requests: list[SimRequest], drivers: list[SimDriver], params: SimParams,
             window: tuple[float, float], moves: dict[str, tuple[float, float]] | None = None,
             tail_s: float = 3 * 3600, max_move_km: float = float("inf"), move_mode: str = "inicio_turno",
             move_origins: dict[str, tuple[float, float]] | None = None, trace: list | None = None,
             fix_m1: bool = False, fix_m2: bool = False, drift: DriftPolicy | None = None,
             unrecoverable: frozenset = frozenset(), reactive: ReactiveConfig | None = None,
             start_at_origin: bool = False) -> SimResult3:
    """Replay de um dia com recomendações de reposicionamento.

    `move_mode="inicio_turno"`: o motorista vai à zona-alvo na primeira disponibilidade da janela,
    partindo da posição real naquele instante, e fica indisponível durante o trajeto.
    `move_mode="fim_do_dia"`: o motorista vai à zona-alvo ao encerrar D (partindo de
    `move_origins[did]`, a última posição real de D) e começa a primeira sessão de D+1 já na zona-alvo;
    não vale para quem já trabalhava mais de 30 min antes da janela.
    Em ambos, o deslocamento real (por rua estimado) precisa respeitar `max_move_km`; caso contrário a
    recomendação conta como não executada (não adesão). O KM executado entra no total (RN031).
    Com `trace` (lista), registra eventos para visualização: (t, tipo, motorista, pedido, (lat, lon), km).
    O rastro não altera nenhuma decisão do replay."""
    if move_mode not in ("inicio_turno", "fim_do_dia"):
        raise ValueError("move_mode inválido")
    move_origins = move_origins or {}
    if len({r.rid for r in requests}) != len(requests) or len({d.did for d in drivers}) != len(drivers):
        raise ValueError("pedidos ou motoristas duplicados")
    moves = dict(moves or {})
    unknown = set(moves) - {d.did for d in drivers}
    w0, w1 = window
    res = SimResult3(signature(requests, drivers, params, window), moves_planned=len(moves))
    res.moves_planned = len(moves)
    for d in unknown:          # recomendação para motorista que não trabalha: não executada
        moves.pop(d)
        res.move_outcomes[d] = "absent"

    def ev(t: float, kind: str, did: str | None, rid: int | None, at: tuple[float, float], km: float | None) -> None:
        if trace is not None:
            trace.append((t, kind, did, rid, at, km))
    horizon = w1 + tail_s
    online = {d.did: False for d in drivers}
    busy_until = {d.did: None for d in drivers}   # None = livre
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

    def commit_blocks(did: str, start: float, end: float) -> bool:
        cs = commits[did]
        k = next_commit[did]
        while k < len(cs) and cs[k][1] <= start:
            k += 1
        return k < len(cs) and cs[k][0] < end

    def job_seconds(did: str, r: SimRequest, t: float) -> tuple[float, float]:
        p = pos_now(did, t)
        km = reta_km(p[0], p[1], r.lat, r.lon) * params.road_factor
        pickup = 3600 * km / params.speed_kmh
        cancel = params.post_accept_cancel and r.post_accept_cancel
        return km, pickup + (0.0 if cancel else r.trip_s)

    def assign(did: str, r: SimRequest, t: float) -> None:
        commit(did, t)
        km, total = job_seconds(did, r, t)
        pickup_s = 3600 * km / params.speed_kmh
        ev(t, "dispatch", did, r.rid, pos[did], km)
        ev(t + pickup_s, "pickup", did, r.rid, (r.lat, r.lon), None)
        res.served += 1
        res.served_ids.add(r.rid)
        res.pickup_km += km
        res.wait_s.append(t - r.t + pickup_s)
        res.served_by_hour[r.hour] = res.served_by_hour.get(r.hour, 0) + 1
        res.pickup_km_by_hour[r.hour] = res.pickup_km_by_hour.get(r.hour, 0.0) + km
        busy_until[did] = t + total
        res.jobs.append((did, t, t + total, "corrida"))
        cancel = params.post_accept_cancel and r.post_accept_cancel
        trip_km = 0.0 if cancel else reta_km(r.lat, r.lon, r.dlat, r.dlon) * params.road_factor
        ev(t + total, "dropoff", did, r.rid, (r.lat, r.lon) if cancel else (r.dlat, r.dlon), trip_km)
        push(t + total, 3, "job_end", (did, (r.lat, r.lon) if cancel else (r.dlat, r.dlon)))

    def eligible(did: str, r: SimRequest, t: float) -> float | None:
        if not online[did] or busy_until[did] is not None or pos[did] is None or r.rid in unrecoverable:
            return None
        p = pos_now(did, t)
        d = reta_km(p[0], p[1], r.lat, r.lon)
        if d > params.radius_km:
            return None
        _, total = job_seconds(did, r, t)
        if commit_blocks(did, t, t + total):
            return None
        return d

    def session_end_at(did: str, t: float) -> float:
        ends = [e for s_, e, _, _ in next(d for d in drivers if d.did == did).sessions if s_ <= t < e]
        return max(ends) if ends else t

    night_done: set[str] = set()
    natural: dict[str, float] = {}
    res.m2 = fix_m2
    dstate: dict = {}
    anchor: dict[str, tuple[float, float]] = {}
    unserved_log: list[tuple[float, float, float]] = []      # (t, lat, lon) de pedidos perdidos (para o reativo)

    def pos_now(did: str, t: float):
        st = dstate.get(did)
        return pos[did] if st is None else st.position(min(t, w1))[0]

    def commit(did: str, t: float) -> None:
        st = dstate.pop(did, None)
        if st is not None:
            p, km = st.position(max(st.t0, min(t, w1)))
            pos[did] = p
            res.drift_km += km

    def try_move(did: str, t: float) -> bool:
        """Executa o reposicionamento pendente; devolve True se o motorista ficou ocupado."""
        if did not in pending_move:
            return False
        lat, lon = pending_move.pop(did)
        if move_mode == "fim_do_dia":       # só vale ao iniciar o dia; depois disso, não adesão
            res.move_outcomes[did] = "busy"
            return False
        if t >= w1:
            res.move_outcomes[did] = "not_free_in_window"
            return False
        km = reta_km(pos[did][0], pos[did][1], lat, lon) * params.road_factor
        end = t + 3600 * km / params.speed_kmh
        if fix_m1 and km > 1e-9 and km <= max_move_km + 1e-9 and end > session_end_at(did, t) + 1e-9:
            res.move_outcomes[did] = "excede_sessao"      # m1: o deslocamento terminaria com o motorista offline
            return False
        if km <= 1e-9 or km > max_move_km + 1e-9 or commit_blocks(did, t, end):
            res.move_outcomes[did] = ("already_there" if km <= 1e-9 else "limit" if km > max_move_km + 1e-9 else "busy")
            return False
        res.move_outcomes[did] = "executed"
        res.move_origins_used[did] = pos[did]
        ev(t, "reposition_start", did, None, pos[did], km)
        ev(end, "reposition_end", did, None, (lat, lon), None)
        res.reposition_km += km
        res.in_service_repos_km += km
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
        elif drift is not None and t < w1 and did in anchor:
            st = drift.start(did, t, pos[did], anchor[did], params.speed_kmh, params.road_factor)
            if st is not None:
                dstate[did] = st

    taken: set[int] = set()

    def reactive_tick(t: float) -> None:
        """B4: aloca livres às origens de pedidos perdidos recentemente (alocação ótima por distância)."""
        from scipy.optimize import linear_sum_assignment

        targets = [(i, lat, lon) for i, (tu, lat, lon) in enumerate(unserved_log)
                   if t - reactive.lookback_s < tu <= t and i not in taken]
        free = [did for did in sorted(online) if online[did] and busy_until[did] is None and pos[did] is not None]
        if not targets or not free:
            return
        big = 1e6
        cost = [[reta_km(*pos_now(did, t), lat, lon) for (_, lat, lon) in targets] for did in free]
        cost = [[c if c <= reactive.max_km else big for c in row] for row in cost]
        rows_, cols_ = linear_sum_assignment(cost)
        for i, j in zip(rows_, cols_):
            if cost[i][j] >= big:
                continue
            did = free[i]
            commit(did, t)
            taken.add(targets[j][0])
            dstate[did] = GoTo(t, pos[did], (targets[j][1], targets[j][2]), params.speed_kmh, params.road_factor)

    if reactive is not None:
        k = w0 + reactive.tick_s
        while k < w1:
            push(k, 6, "tick", None)
            k += reactive.tick_s

    while events:
        t, _, _, kind, data = heapq.heappop(events)
        if kind == "sess_start":
            did, lat, lon = data
            online[did] = True
            first_event = did not in night_done
            night_done.add(did)
            if busy_until[did] is None:
                if lat is not None:
                    pos[did] = (lat, lon)
                if start_at_origin and move_mode == "fim_do_dia" and first_event and first_start[did] >= w0 - 1800:
                    o = move_origins.get(did)
                    if o is not None:
                        pos[did] = o          # m2 (origem): os dois braços começam onde o motorista largou em D
                if fix_m2 and move_mode == "fim_do_dia" and first_event and lat is not None:
                    o = move_origins.get(did)
                    if o is not None and first_start[did] >= w0 - 1800:
                        natural[did] = reta_km(o[0], o[1], lat, lon) * params.road_factor
                        res.overnight_km += natural[did]
                        res.overnight_drivers += 1
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
                        ev(t, "reposition_start", did, None, origin, km)
                        ev(t, "reposition_end", did, None, target, None)
                        res.reposition_km += km
                        if fix_m2:
                            res.overnight_km += km - natural.get(did, 0.0)    # o alvo substitui o trecho natural
                        res.moves_executed += 1
                        res.jobs.append((did, t, t, "reposicionamento_fim_do_dia"))
                        pos[did] = target
                if did not in anchor and pos[did] is not None:
                    anchor[did] = pos[did]
                become_free(did, t)
        elif kind == "sess_end":
            commit(data, t)
            online[data] = False
        elif kind == "commit_start":
            did, i = data
            s, e, lat, lon = commits[did][i]
            commit(did, t)
            if pending_move.pop(did, None) is not None:   # ocupado antes da primeira disponibilidade
                res.move_outcomes[did] = "busy"
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
            ev(t, "request_created", None, r.rid, (r.lat, r.lon), None)
            options = [(d, did) for did in online if (d := eligible(did, r, t)) is not None]
            if options:
                _, did = min(options)
                assign(did, r, t)
            else:
                waiting[r.rid] = r
                patience = params.patience_s if r.patience_s is None else min(params.patience_s, r.patience_s)
                push(t + patience, 5, "deadline", r.rid)
        elif kind == "deadline":
            gone = waiting.pop(data, None)
            if gone is not None:
                ev(t, "request_unserved", None, gone.rid, (gone.lat, gone.lon), None)
                unserved_log.append((t, gone.lat, gone.lon))
        elif kind == "tick":
            reactive_tick(t)
    for did in pending_move:
        res.move_outcomes[did] = "not_free_in_window"
    return res
