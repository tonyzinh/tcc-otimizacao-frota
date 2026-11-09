"""Motor de simulação de eventos discretos (despacho imediato ou em lotes, compromissos externos, reposicionamento opcional).

Tempos em segundos desde a meia-noite local do dia simulado; distâncias por rua estimadas = linha reta × fator (nunca odômetro), ou
distância pela rede quando uma métrica é fornecida (cenários sintéticos).
"""

from __future__ import annotations

import heapq

from tcc_frota.domain.entities import SimDriver, SimParams, SimRequest, SimResult, reta_km, signature


def _merge(intervals) -> list[tuple[float, float, float, float]]:
    out: list[list[float]] = []
    for s, e, lat, lon in sorted(intervals):
        if out and s < out[-1][1]:
            if e > out[-1][1]:
                out[-1][1:] = [e, lat, lon]
        else:
            out.append([s, e, lat, lon])
    return [tuple(x) for x in out]


def _merge_com_origem(intervals, origens):
    """Como `_merge`, preservando a origem (lat, lon) do primeiro compromisso de cada grupo sobreposto."""
    itens = sorted(zip(intervals, origens, strict=True), key=lambda x: x[0])
    out: list[list] = []
    for (s, e, lat, lon), o in itens:
        if out and s < out[-1][1]:
            if e > out[-1][1]:
                out[-1][1:4] = [e, lat, lon]
        else:
            out.append([s, e, lat, lon, o])
    return [tuple(x[:4]) for x in out], [x[4] for x in out]


def simulate(
    requests: list[SimRequest],
    drivers: list[SimDriver],
    params: SimParams,
    window: tuple[float, float],
    moves: dict[str, tuple[float, float]] | None = None,
    tail_s: float = 3 * 3600,
    max_move_km: float = float("inf"),
    move_mode: str = "inicio_turno",
    move_origins: dict[str, tuple[float, float]] | None = None,
    trace: list | None = None,
    commit_origins: dict[str, list[tuple[float, float] | None]] | None = None,
    batch_s: float | None = None,
    assigner=None,
    metric=None,
) -> SimResult:
    """Replay de um dia com recomendações de reposicionamento.

    `move_mode="inicio_turno"`: o motorista vai à zona-alvo na primeira disponibilidade da janela,
    partindo da posição real naquele instante, e fica indisponível durante o trajeto.
    `move_mode="fim_do_dia"`: o motorista vai à zona-alvo ao encerrar D (partindo de
    `move_origins[did]`, a última posição real de D) e começa a primeira sessão de D+1 já na zona-alvo;
    não vale para quem já trabalhava mais de 30 min antes da janela.
    Em ambos, o deslocamento real (por rua estimado) precisa respeitar `max_move_km`; caso contrário a
    recomendação conta como não executada (não adesão). O KM executado entra no total (RN031).
    Com `trace` (lista), registra eventos para visualização: (t, tipo, motorista, pedido, (lat, lon), km).
    O rastro não altera nenhuma decisão do replay.

    `commit_origins` (opcional; `commit_origins[did][i]` = origem do i-ésimo compromisso na ordem de `sorted(d.commitments)`)
    liga o MODO COM DESLOCAMENTO: uma tarefa só é aceita se, ao terminar, houver tempo para ir da posição final até a origem do
    compromisso seguinte (distância por rua estimada / velocidade); ao iniciar o compromisso o motorista parte da posição em que
    ficou livre e o km dessa aproximação é registrado em `commit_approach_km` (fora do KM vazio comparado). Se mesmo assim a folga
    for insuficiente (posição de entrada incompatível), `commit_events` registra causa "entrada" e o déficit; causa "politica"
    (uma tarefa simulada que impeça a chegada) não deve ocorrer e é contada. Sem `commit_origins`, comportamento v2 inalterado.

    `metric` (opcional; objeto com `.km(lat1, lon1, lat2, lon2)` = km pela rede viária) substitui Haversine x fator rua/reta em TODAS as
    distâncias (busca, viagem, reposicionamento, aproximação a compromissos) e passa a medir o raio de despacho por via. Sem `metric`,
    comportamento inalterado.

    `batch_s` + `assigner` ligam o DESPACHO EM LOTE: pedidos esperam até o próximo múltiplo de `batch_s` (a espera causada pela
    janela é contada) e, em cada instante de lote, `assigner(t, pedidos_em_espera, candidatos)` devolve pares (rid, did).
    `candidatos[rid]` = lista ordenada [(distância em linha reta, did)] só com motoristas elegíveis (online, livres, dentro do raio e
    sem conflito com compromisso). Pedido nunca é considerado antes de chegar. Motorista liberado espera o próximo lote. Sem `batch_s`,
    o despacho é o imediato da v2 (motorista elegível mais próximo no instante do pedido), inalterado."""
    if move_mode not in ("inicio_turno", "fim_do_dia"):
        raise ValueError("move_mode inválido")
    move_origins = move_origins or {}
    if len({r.rid for r in requests}) != len(requests) or len({d.did for d in drivers}) != len(drivers):
        raise ValueError("pedidos ou motoristas duplicados")
    moves = dict(moves or {})
    unknown = set(moves) - {d.did for d in drivers}
    w0, w1 = window
    res = SimResult(signature(requests, drivers, params, window), moves_planned=len(moves))
    res.moves_planned = len(moves)
    for d in unknown:  # recomendação para motorista que não trabalha: não executada
        moves.pop(d)
        res.move_outcomes[d] = "absent"

    def dkm(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
        if metric is not None:
            return metric.km(a_lat, a_lon, b_lat, b_lon)
        return reta_km(a_lat, a_lon, b_lat, b_lon) * params.road_factor

    def ev(t: float, kind: str, did: str | None, rid: int | None, at: tuple[float, float], km: float | None) -> None:
        if trace is not None:
            trace.append((t, kind, did, rid, at, km))

    horizon = w1 + tail_s
    online = {d.did: False for d in drivers}
    busy_until = {d.did: None for d in drivers}  # None = livre
    pos: dict[str, tuple[float, float] | None] = {d.did: None for d in drivers}
    com_deslocamento = commit_origins is not None
    commits: dict = {}
    cor: dict = {}
    for d in drivers:
        if com_deslocamento:
            ords = sorted(d.commitments)
            ors = (commit_origins or {}).get(d.did) or [None] * len(ords)
            if len(ors) != len(ords):
                raise ValueError("commit_origins desalinhado com os compromissos")
            commits[d.did], cor[d.did] = _merge_com_origem(ords, ors)
        else:
            commits[d.did], cor[d.did] = _merge(d.commitments), []
    free_since: dict[str, float | None] = {d.did: None for d in drivers}
    pos_source: dict[str, str] = {d.did: "desconhecida" for d in drivers}
    next_commit = {d.did: 0 for d in drivers}
    pending_move = dict(moves)
    first_start = {d.did: min((x[0] for x in d.sessions), default=float("inf")) for d in drivers}
    waiting: dict[int, SimRequest] = {}
    ticks: set[float] = set()
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

    def commit_blocks(did: str, start: float, end: float, end_pos: tuple[float, float] | None = None) -> bool:
        cs = commits[did]
        k = next_commit[did]
        while k < len(cs) and cs[k][1] <= start:
            k += 1
        if k >= len(cs):
            return False
        folga_fim = end
        if com_deslocamento and end_pos is not None and cor[did][k] is not None:
            o = cor[did][k]
            folga_fim = end + 3600 * dkm(end_pos[0], end_pos[1], o[0], o[1]) / params.speed_kmh
        return cs[k][0] < folga_fim

    def job_seconds(did: str, r: SimRequest) -> tuple[float, float]:
        km = dkm(pos[did][0], pos[did][1], r.lat, r.lon)
        pickup = 3600 * km / params.speed_kmh
        cancel = params.post_accept_cancel and r.post_accept_cancel
        return km, pickup + (0.0 if cancel else r.trip_s)

    def assign(did: str, r: SimRequest, t: float) -> None:
        km, total = job_seconds(did, r)
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
        pos_source[did] = "corrida"
        res.jobs.append((did, t, t + total, "corrida"))
        cancel = params.post_accept_cancel and r.post_accept_cancel
        trip_km = 0.0 if cancel else dkm(r.lat, r.lon, r.dlat, r.dlon)
        ev(t + total, "dropoff", did, r.rid, (r.lat, r.lon) if cancel else (r.dlat, r.dlon), trip_km)
        push(t + total, 3, "job_end", (did, (r.lat, r.lon) if cancel else (r.dlat, r.dlon)))

    def eligible(did: str, r: SimRequest, t: float) -> float | None:
        if not online[did] or busy_until[did] is not None or pos[did] is None:
            return None
        d = dkm(pos[did][0], pos[did][1], r.lat, r.lon) if metric is not None else reta_km(pos[did][0], pos[did][1], r.lat, r.lon)
        if d > params.radius_km:
            return None
        _, total = job_seconds(did, r)
        cancel = params.post_accept_cancel and r.post_accept_cancel
        if commit_blocks(did, t, t + total, (r.lat, r.lon) if cancel else (r.dlat, r.dlon)):
            return None
        return d

    def try_move(did: str, t: float) -> bool:
        """Executa o reposicionamento pendente; devolve True se o motorista ficou ocupado."""
        if did not in pending_move:
            return False
        lat, lon = pending_move.pop(did)
        if move_mode == "fim_do_dia":  # só vale ao iniciar o dia; depois disso, não adesão
            res.move_outcomes[did] = "busy"
            return False
        if t >= w1:
            res.move_outcomes[did] = "not_free_in_window"
            return False
        km = dkm(pos[did][0], pos[did][1], lat, lon)
        end = t + 3600 * km / params.speed_kmh
        if km <= 1e-9 or km > max_move_km + 1e-9 or commit_blocks(did, t, end, (lat, lon)):
            res.move_outcomes[did] = "already_there" if km <= 1e-9 else "limit" if km > max_move_km + 1e-9 else "busy"
            return False
        res.move_outcomes[did] = "executed"
        res.move_origins_used[did] = pos[did]
        ev(t, "reposition_start", did, None, pos[did], km)
        ev(end, "reposition_end", did, None, (lat, lon), None)
        res.reposition_km += km
        res.moves_executed += 1
        busy_until[did] = end
        pos_source[did] = "reposicionamento"
        res.jobs.append((did, t, end, "reposicionamento"))
        push(end, 3, "job_end", (did, (lat, lon)))
        return True

    def agendar_lote(t: float) -> None:
        nxt = t if batch_s and abs(t / batch_s - round(t / batch_s)) < 1e-9 else (int(t // batch_s) + 1) * batch_s
        if nxt not in ticks:
            ticks.add(nxt)
            push(nxt, 4.5, "batch_tick", nxt)

    def become_free(did: str, t: float) -> None:
        busy_until[did] = None
        free_since[did] = t
        if not online[did] or pos[did] is None:
            return
        if try_move(did, t):
            return
        if batch_s:  # em lote, quem decide é o próximo instante de lote
            return
        best = None
        for rid in sorted(waiting):  # FIFO: pedido mais antigo primeiro
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
                    pos_source[did] = "sessao"
                    free_since[did] = t
                if move_mode == "fim_do_dia" and did in pending_move:
                    target = pending_move.pop(did)
                    origin = move_origins.get(did) or pos[did]
                    km = dkm(origin[0], origin[1], target[0], target[1])
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
                        res.moves_executed += 1
                        res.jobs.append((did, t, t, "reposicionamento_fim_do_dia"))
                        pos[did] = target
                become_free(did, t)
        elif kind == "sess_end":
            online[data] = False
        elif kind == "commit_start":
            did, i = data
            s, e, lat, lon = commits[did][i]
            if pending_move.pop(did, None) is not None:  # ocupado antes da primeira disponibilidade
                res.move_outcomes[did] = "busy"
            if busy_until[did] is not None:
                raise AssertionError("compromisso sobreposto a tarefa simulada (RN017)")
            if com_deslocamento:
                o = cor[did][i]
                ev_c: dict = {"did": did, "i": i, "inicio_s": s, "origem_conhecida": o is not None, "posicao_fonte": pos_source[did]}
                if o is None or pos[did] is None or free_since[did] is None:
                    ev_c["classe"] = "incerta (origem ou posição desconhecida; sem deslocamento modelado)"
                else:
                    km_c = dkm(pos[did][0], pos[did][1], o[0], o[1])
                    need = 3600 * km_c / params.speed_kmh
                    deficit = max(0.0, need - max(0.0, s - free_since[did]))
                    res.commit_approach_km += km_c
                    ev_c.update({"aproximacao_km": km_c, "tempo_necessario_s": need, "folga_s": s - free_since[did], "deficit_s": deficit})
                    if deficit > 1e-6:
                        causa = "politica" if pos_source[did] in ("corrida", "reposicionamento") else "entrada"
                        ev_c["classe"] = f"insuficiente_por_{causa}"
                    else:
                        ev_c["classe"] = "viavel"
                res.commit_events.append(ev_c)
                pos_source[did] = "compromisso"
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
            if batch_s:
                waiting[r.rid] = r
                patience = params.patience_s if r.patience_s is None else min(params.patience_s, r.patience_s)
                push(t + patience, 5, "deadline", r.rid)
                agendar_lote(t)
                continue
            options = [(d, did) for did in online if (d := eligible(did, r, t)) is not None]
            if options:
                _, did = min(options)
                assign(did, r, t)
            else:
                waiting[r.rid] = r
                patience = params.patience_s if r.patience_s is None else min(params.patience_s, r.patience_s)
                push(t + patience, 5, "deadline", r.rid)
        elif kind == "batch_tick":
            ticks.discard(data)
            pend = sorted(waiting.values(), key=lambda r: (r.t, r.rid))
            cands = {}
            for r in pend:
                lst = sorted((d, did) for did in online if (d := eligible(did, r, t)) is not None)
                if lst:
                    cands[r.rid] = lst
            if cands:
                pares = assigner(t, pend, cands)
                usados_r: set[int] = set()
                usados_d: set[str] = set()
                for rid, did in pares:
                    if rid in usados_r or did in usados_d or rid not in waiting or all(x[1] != did for x in cands.get(rid, ())):
                        raise AssertionError("atribuição em lote inválida (duplicada ou inelegível)")
                    usados_r.add(rid)
                    usados_d.add(did)
                    assign(did, waiting.pop(rid), t)
            if waiting:
                agendar_lote(t + batch_s)
        elif kind == "deadline":
            gone = waiting.pop(data, None)
            if gone is not None:
                ev(t, "request_unserved", None, gone.rid, (gone.lat, gone.lon), None)
    for did in pending_move:
        res.move_outcomes[did] = "not_free_in_window"
    return res
