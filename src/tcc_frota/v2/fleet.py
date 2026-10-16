"""Mundo observado de D+1 e escada de informação da frota (Fase 3).

O mundo (pedidos, sessões, posições e compromissos reais) é idêntico em todos os cenários. O plano é
feito às 20h de D com um de três regimes:

- A (D+1 estrito): quem trabalha e quando é previsto pela presença em dias comparáveis (limiar 50%,
  como DT011); posição = última posição conhecida até o corte.
- B (escala conhecida): a lista de quem trabalha amanhã é conhecida; o plano é fechado no fim de D
  com a última posição de D (motoristas dormem onde largam); horário previsto como em A. Não usa
  nada de D+1 além da escala. Realista só se houver escala de turnos (DECISÃO DO ALUNO, a confirmar
  com a empresa). Variante de sensibilidade: posição às 20h.
- C (oráculo): posições e horários reais de D+1. Viola o corte; serve só para diagnóstico.
"""
from __future__ import annotations

import bisect
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from statistics import median

from tcc_frota.v2.rules import TZ, WORKING_STATES
from tcc_frota.v2.sim import SimDriver, SimRequest

REGIMES = ("A", "B", "C")
CUT_HOUR = 20


def seconds(ts: datetime, day: date) -> float:
    return (ts - datetime.combine(day, time(0), TZ)).total_seconds()


@dataclass(frozen=True)
class PlannedDriver:
    did: str
    lat: float
    lon: float
    start_h: float   # hora prevista de início (horas desde a meia-noite de D+1)
    end_h: float


class FleetIndex:
    """Índices por motorista e data sobre as fotos, sessões e corridas aceitas."""

    def __init__(self, snapshot: list[dict], sessions: list[dict], rides: list[dict]):
        self.snaps: dict[str, list[dict]] = defaultdict(list)
        self.by_date: dict[date, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        for row in snapshot:
            if row["estado"] in WORKING_STATES and row["fl_coordenada_valida"]:
                self.snaps[row["motorista_pseud"]].append(row)
                self.by_date[row["ts_snapshot"].date()][row["motorista_pseud"]].append(row)
        for rows in self.snaps.values():
            rows.sort(key=lambda r: r["ts_snapshot"])
        self.snap_times = {d: [r["ts_snapshot"] for r in rows] for d, rows in self.snaps.items()}
        self.sessions: dict[date, list[dict]] = defaultdict(list)
        for s in sessions:
            day = s["ts_inicio"].date()
            for k in range((s["ts_fim"].date() - day).days + 1):
                self.sessions[day + timedelta(days=k)].append(s)
        self.rides: dict[date, list[dict]] = defaultdict(list)
        for r in rides:
            for k in range((r["end"].date() - r["start"].date()).days + 1):
                self.rides[r["start"].date() + timedelta(days=k)].append(r)
        self.dates = sorted(self.by_date)

    def last_position(self, did: str, until: datetime) -> tuple[float, float] | None:
        times = self.snap_times.get(did)
        if not times:
            return None
        i = bisect.bisect_right(times, until) - 1
        if i < 0:
            return None
        row = self.snaps[did][i]
        return row["lat"], row["lon"]

    def present_in_window(self, day: date, w0: float, w1: float) -> dict[str, tuple[float, float]]:
        """Motoristas com foto de trabalho na janela do dia: (primeira, última) hora decimal."""
        out = {}
        for did, rows in self.by_date.get(day, {}).items():
            hours = [r["ts_snapshot"].hour + r["ts_snapshot"].minute / 60 for r in rows]
            inside = [h for h in hours if w0 / 3600 <= h < w1 / 3600]
            if inside:
                out[did] = (min(inside), max(inside) + 1 / 6)
        return out


SCHEDULED_LEAD = timedelta(minutes=15)


def rides_from_silver(solicitacoes: list[dict]) -> list[dict]:
    """Corridas aceitas com motorista: candidatas a compromisso externo no mundo simulado.

    Imediatas ocupam o motorista desde o aceite. Agendadas são aceitas horas ou dias antes; ocupam
    o motorista só a partir de `SCHEDULED_LEAD` antes da chegada (ou do início, ou do horário
    agendado), nunca antes do aceite.
    """
    out = []
    for r in solicitacoes:
        if not r["fl_aceito"] or r["motorista_pseud"] is None or r["ts_aceite"] is None:
            continue
        start = r["ts_aceite"]
        if not r["fl_imediata"]:
            anchor = r["ts_chegada"] or r["ts_inicio"] or r["ts_agendamento"]
            if anchor is not None:
                start = max(start, anchor - SCHEDULED_LEAD)
        end = r["ts_fim"] or r["ts_status_final"] or (start + SCHEDULED_LEAD)
        if end <= start:
            continue
        lat = r["lat_destino_real"] if r["lat_destino_real"] is not None else r["lat_destino"]
        lon = r["lon_destino_real"] if r["lon_destino_real"] is not None else r["lon_destino"]
        if r["status"] != "CorridaEncerrada" or lat is None:
            lat, lon = r["lat_origem"], r["lon_origem"]
        out.append({"codigo": r["codigo"], "did": r["motorista_pseud"], "start": start, "end": end,
                    "lat": lat, "lon": lon})
    return out


def build_world(index: FleetIndex, requests_day: list[dict], target: date, window: tuple[int, int],
                trip_seconds_fallback, tail_h: int = 3) -> tuple[list[SimRequest], list[SimDriver]]:
    """Pedidos do universo na janela e motoristas reais de D+1 com sessões e compromissos."""
    w0, w1 = window[0] * 3600.0, window[1] * 3600.0
    horizon = w1 + tail_h * 3600
    reqs = []
    in_window: set[int] = set()
    for r in requests_day:
        t = seconds(r["ts_pedido"], target)
        if not (w0 <= t < w1):
            continue
        in_window.add(r["codigo"])
        trip = r["dur_viagem_obs_s"] or trip_seconds_fallback(r)
        reqs.append(SimRequest(r["codigo"], t, r["lat_origem"], r["lon_origem"], r["lat_destino"], r["lon_destino"],
                               trip, r["s_espera_ate_desistir"], r["fl_cancelada_pos_aceite"], r["hora_local"],
                               r["h3_r7_origem"] or ""))
    sessions: dict[str, list] = defaultdict(list)
    for s in index.sessions.get(target, []):
        start, end = seconds(s["ts_inicio"], target), seconds(s["ts_fim"], target)
        if end <= w0 or start >= horizon:
            continue
        if start < w0:
            p = index.last_position(s["motorista_pseud"], datetime.combine(target, time(0), TZ) + timedelta(seconds=w0))
            lat, lon = p if p else (s["lat_inicio"], s["lon_inicio"])
        else:
            lat, lon = s["lat_inicio"], s["lon_inicio"]
        if lat is None:
            continue
        sessions[s["motorista_pseud"]].append((start, end, lat, lon))
    commits: dict[str, list] = defaultdict(list)
    for c in index.rides.get(target, []):
        if c["codigo"] in in_window or c["did"] not in sessions:
            continue
        start, end = seconds(c["start"], target), seconds(c["end"], target)
        if end <= w0 or start >= horizon:
            continue
        commits[c["did"]].append((start, end, c["lat"], c["lon"]))
    drivers = [SimDriver(did, tuple(sorted(v)), tuple(sorted(commits.get(did, ())))) for did, v in sorted(sessions.items())]
    return sorted(reqs, key=lambda r: (r.t, r.rid)), drivers


def _comparable_days(index: FleetIndex, target: date, lookback: int = 28) -> list[date]:
    cut_day = target - timedelta(days=1)
    pool = [d for d in index.dates if cut_day - timedelta(days=lookback) < d <= cut_day]
    same = [d for d in pool if d.weekday() == target.weekday()]
    return same if len(same) >= 2 else pool


def end_of_day(target: date) -> datetime:
    """Último instante de D (= meia-noite de D+1, exclusiva)."""
    return datetime.combine(target, time(0), TZ) - timedelta(microseconds=1)


def planned_fleet(regime: str, index: FleetIndex, target: date, window: tuple[int, int],
                  world: list[SimDriver], min_presence: float = 0.5,
                  position_cut_hour: int | None = None) -> tuple[list[PlannedDriver], dict]:
    """Frota que o planejador enxerga no corte, por regime, e diagnóstico de precisão/revocação.

    Posição: A usa o corte de 20h; B usa o fim de D (ou `position_cut_hour`, se dado)."""
    w0, w1 = window[0] * 3600.0, window[1] * 3600.0
    hour = position_cut_hour if position_cut_hour is not None else (CUT_HOUR if regime == "A" else 24)
    cut = end_of_day(target) if hour >= 24 else datetime.combine(target - timedelta(days=1), time(hour), TZ)
    actual = {d.did for d in world}
    days = _comparable_days(index, target)
    presence: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for day in days:
        for did, span in index.present_in_window(day, w0, w1).items():
            presence[did].append(span)
    typical = {did: (median(s for s, _ in spans), median(e for _, e in spans)) for did, spans in presence.items()}
    if regime == "A":
        chosen = sorted(did for did, spans in presence.items() if len(spans) >= min_presence * max(1, len(days)))
    elif regime == "B":
        chosen = sorted(actual)
    elif regime == "C":
        out = []
        for d in world:
            first = min((s for s in d.sessions if s[1] > w0), default=None)
            if first is None:
                continue
            start, _, lat, lon = first
            end = max(e for _, e, _, _ in d.sessions)
            out.append(PlannedDriver(d.did, lat, lon, max(start, w0) / 3600, min(end, w1) / 3600))
        return out, {"previstos": len(out), "reais": len(actual), "acertos": len(out), "sem_posicao": 0,
                     "dias_comparaveis": len(days)}
    else:
        raise ValueError(regime)
    out, missing = [], 0
    for did in chosen:
        p = index.last_position(did, cut)
        if p is None:
            missing += 1
            continue
        start, end = typical.get(did, (w0 / 3600, w1 / 3600))
        out.append(PlannedDriver(did, p[0], p[1], start, end))
    hits = len({d.did for d in out} & actual)
    return out, {"previstos": len(out), "reais": len(actual), "acertos": hits, "sem_posicao": missing,
                 "dias_comparaveis": len(days)}
