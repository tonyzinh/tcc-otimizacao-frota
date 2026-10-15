/**
 * Motor visual do replay: transforma eventos de um cenário em trilhas por veículo e quadros
 * interpolados. É apresentação pura — não decide despacho nem recalcula indicadores científicos;
 * os quilômetros acumulados vêm dos eventos (Haversine), não das curvas desenhadas.
 */
import { cumulativeLengths, illustrativeCurve, pointAlong } from '@/lib/geo'
import { hashString } from '@/lib/random'
import { toEpoch } from '@/lib/time'
import type { CumulativeCounters, DaySnapshot, LngLat, ReplayFrame, ScenarioRun, VehicleFrame, VehicleState } from '@/types'

export interface TrackSegment {
  vehicleId: string
  kind: VehicleState
  t0: number
  t1: number
  path: LngLat[]
  lengths: number[]
  /** KM do evento (Haversine). Zero para segmentos parados. */
  km: number
  requestId: string | null
  movementId: string | null
}

export interface Trail {
  id: string
  vehicleId: string
  kind: 'repositioning' | 'to_pickup' | 'on_trip'
  path: LngLat[]
  /** Segundos desde o início da janela, um por vértice. */
  timestamps: number[]
  t0: number
  t1: number
  km: number
}

export type RequestDisplayState = 'waiting' | 'served' | 'unserved'

export interface RequestTimeline {
  id: string
  origin: LngLat
  createdAt: number
  outcome: 'served' | 'unserved'
  pickupAt: number | null
  vehicleId: string | null
  pickupKm: number | null
}

export interface ReplayModel {
  windowStart: number
  windowEnd: number
  /** Fim da linha do tempo: fim da janela ou último evento (viagens iniciadas na janela terminam depois). */
  timelineEnd: number
  tracks: Map<string, TrackSegment[]>
  trails: Trail[]
  requests: RequestTimeline[]
  /** Instantes únicos e ordenados de eventos (para avançar/retroceder por evento). */
  eventTimes: number[]
}

function staticSegment(vehicleId: string, kind: VehicleState, t0: number, t1: number, at: LngLat): TrackSegment {
  return { vehicleId, kind, t0, t1, path: [at], lengths: [0], km: 0, requestId: null, movementId: null }
}

function movingSegment(
  vehicleId: string,
  kind: VehicleState,
  t0: number,
  t1: number,
  path: LngLat[],
  km: number,
  refs: { requestId?: string; movementId?: string },
): TrackSegment {
  return {
    vehicleId,
    kind,
    t0,
    t1: Math.max(t1, t0 + 1),
    path,
    lengths: cumulativeLengths(path),
    km,
    requestId: refs.requestId ?? null,
    movementId: refs.movementId ?? null,
  }
}

function bend(seed: string, magnitude: number): number {
  const h = hashString(seed)
  return ((h & 1) === 0 ? 1 : -1) * magnitude * (0.6 + ((h >>> 1) % 40) / 100)
}

export function buildReplayModel(snapshot: DaySnapshot, run: ScenarioRun): ReplayModel {
  const windowStart = toEpoch(snapshot.window.start)
  const windowEnd = toEpoch(snapshot.window.end)
  const movements = new Map(run.movements.map((m) => [m.id, m]))

  // Intervalos ocupados por veículo, a partir dos eventos.
  const busy = new Map<string, TrackSegment[]>()
  const pendingDispatch = new Map<string, { t: number; from: LngLat; km: number; requestId: string }>()
  const pendingPickup = new Map<string, { t: number; at: LngLat; requestId: string }>()
  const pendingReposition = new Map<string, { t: number; km: number; movementId: string }>()
  const requests = new Map<string, RequestTimeline>()
  const eventTimes = new Set<number>()

  const pushBusy = (segment: TrackSegment) => {
    const list = busy.get(segment.vehicleId) ?? []
    list.push(segment)
    busy.set(segment.vehicleId, list)
  }

  for (const e of run.events) {
    const t = toEpoch(e.t)
    eventTimes.add(t)
    switch (e.type) {
      case 'request_created':
        if (e.requestId) {
          requests.set(e.requestId, {
            id: e.requestId,
            origin: e.position,
            createdAt: t,
            outcome: 'unserved',
            pickupAt: null,
            vehicleId: null,
            pickupKm: null,
          })
        }
        break
      case 'request_unserved':
        break
      case 'dispatch':
        if (e.vehicleId && e.requestId) {
          pendingDispatch.set(e.vehicleId, { t, from: e.position, km: e.km ?? 0, requestId: e.requestId })
          const r = requests.get(e.requestId)
          if (r) {
            r.outcome = 'served'
            r.vehicleId = e.vehicleId
            r.pickupKm = e.km
          }
        }
        break
      case 'pickup':
        if (e.vehicleId) {
          const d = pendingDispatch.get(e.vehicleId)
          if (d) {
            const path = illustrativeCurve(d.from, e.position, bend(`${d.requestId}:p`, 0.08), 10)
            pushBusy(movingSegment(e.vehicleId, 'to_pickup', d.t, t, path, d.km, { requestId: d.requestId }))
            pendingDispatch.delete(e.vehicleId)
          }
          pendingPickup.set(e.vehicleId, { t, at: e.position, requestId: e.requestId ?? '' })
          const r = e.requestId ? requests.get(e.requestId) : undefined
          if (r) r.pickupAt = t
        }
        break
      case 'dropoff':
        if (e.vehicleId) {
          const p = pendingPickup.get(e.vehicleId)
          if (p) {
            const path = illustrativeCurve(p.at, e.position, bend(`${p.requestId}:t`, 0.1), 14)
            pushBusy(movingSegment(e.vehicleId, 'on_trip', p.t, t, path, e.km ?? 0, { requestId: p.requestId }))
            pendingPickup.delete(e.vehicleId)
          }
        }
        break
      case 'reposition_start':
        if (e.vehicleId && e.movementId) {
          pendingReposition.set(e.vehicleId, { t, km: e.km ?? 0, movementId: e.movementId })
        }
        break
      case 'reposition_end':
        if (e.vehicleId) {
          const r = pendingReposition.get(e.vehicleId)
          const movement = r ? movements.get(r.movementId) : undefined
          if (r && movement) {
            const path = movement.executedPath ?? [movement.executedFrom ?? movement.plannedFrom, movement.to]
            pushBusy(movingSegment(e.vehicleId, 'repositioning', r.t, t, path, r.km, { movementId: r.movementId }))
          }
          pendingReposition.delete(e.vehicleId)
        }
        break
    }
  }

  const sortedTimes = [...eventTimes].sort((a, b) => a - b)
  const timelineEnd = Math.max(windowEnd, sortedTimes[sortedTimes.length - 1] ?? windowEnd)

  // Preenche lacunas: indisponível antes/depois do expediente e parado entre deslocamentos.
  const tracks = new Map<string, TrackSegment[]>()
  for (const f of snapshot.fleetAtStart) {
    const from = toEpoch(f.availableFrom)
    const until = toEpoch(f.availableUntil)
    const moving = (busy.get(f.vehicleId) ?? []).sort((a, b) => a.t0 - b.t0)
    const segments: TrackSegment[] = []
    let cursor = windowStart
    let pos: LngLat = f.position
    const preState: VehicleState = f.state === 'on_trip' ? 'on_trip' : 'unavailable'
    if (from > windowStart) {
      segments.push(staticSegment(f.vehicleId, preState, windowStart, from, pos))
      cursor = from
    }
    for (const seg of moving) {
      if (seg.t0 > cursor) segments.push(staticSegment(f.vehicleId, 'idle', cursor, seg.t0, pos))
      segments.push(seg)
      cursor = Math.max(cursor, seg.t1)
      pos = seg.path[seg.path.length - 1] ?? pos
    }
    const idleUntil = Math.max(cursor, until >= windowEnd ? timelineEnd : until)
    if (idleUntil > cursor) segments.push(staticSegment(f.vehicleId, 'idle', cursor, idleUntil, pos))
    const end = Math.max(timelineEnd, cursor)
    if (end > idleUntil) segments.push(staticSegment(f.vehicleId, 'unavailable', idleUntil, end, pos))
    tracks.set(f.vehicleId, segments)
  }

  const trails: Trail[] = []
  for (const segments of tracks.values()) {
    for (const seg of segments) {
      if (seg.kind !== 'repositioning' && seg.kind !== 'to_pickup' && seg.kind !== 'on_trip') continue
      const total = seg.lengths[seg.lengths.length - 1] ?? 0
      const span = (seg.t1 - seg.t0) / 1000
      const base = (seg.t0 - windowStart) / 1000
      trails.push({
        id: `${seg.vehicleId}:${seg.t0}`,
        vehicleId: seg.vehicleId,
        kind: seg.kind,
        path: seg.path,
        timestamps: seg.lengths.map((l) => base + (total > 0 ? (l / total) * span : 0)),
        t0: seg.t0,
        t1: seg.t1,
        km: seg.km,
      })
    }
  }

  return {
    windowStart,
    windowEnd,
    timelineEnd,
    tracks,
    trails,
    requests: [...requests.values()].sort((a, b) => a.createdAt - b.createdAt),
    eventTimes: sortedTimes,
  }
}

function findSegment(segments: readonly TrackSegment[], t: number): TrackSegment | null {
  if (segments.length === 0) return null
  let lo = 0
  let hi = segments.length - 1
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    const s = segments[mid]!
    if (t < s.t0) hi = mid - 1
    else if (t >= s.t1) lo = mid + 1
    else return s
  }
  return t >= segments[segments.length - 1]!.t1 ? segments[segments.length - 1]! : segments[0]!
}

export function vehicleFrameAt(segments: readonly TrackSegment[], t: number): VehicleFrame | null {
  const seg = findSegment(segments, t)
  if (!seg) return null
  const progress = seg.t1 > seg.t0 ? Math.min(1, Math.max(0, (t - seg.t0) / (seg.t1 - seg.t0))) : 1
  return { vehicleId: seg.vehicleId, position: pointAlong(seg.path, seg.lengths, progress), state: seg.kind, progress }
}

export function requestStateAt(request: RequestTimeline, t: number): RequestDisplayState | null {
  if (t < request.createdAt) return null
  if (request.outcome === 'unserved') return 'unserved'
  return request.pickupAt !== null && t >= request.pickupAt ? 'served' : 'waiting'
}

export function countersAt(model: ReplayModel, t: number): CumulativeCounters {
  let pickupKm = 0
  let repositionKm = 0
  for (const trail of model.trails) {
    if (trail.kind === 'on_trip' || t <= trail.t0) continue
    const f = t >= trail.t1 ? 1 : (t - trail.t0) / (trail.t1 - trail.t0)
    if (trail.kind === 'to_pickup') pickupKm += trail.km * f
    else repositionKm += trail.km * f
  }
  let served = 0
  let unserved = 0
  let pending = 0
  for (const r of model.requests) {
    const state = requestStateAt(r, t)
    if (state === 'served') served += 1
    else if (state === 'unserved') unserved += 1
    else if (state === 'waiting') pending += 1
  }
  return { pickupKm, repositionKm, emptyKm: pickupKm + repositionKm, served, unserved, pending }
}

export function frameAt(model: ReplayModel, t: number): ReplayFrame {
  const vehicles: VehicleFrame[] = []
  for (const segments of model.tracks.values()) {
    const frame = vehicleFrameAt(segments, t)
    if (frame) vehicles.push(frame)
  }
  const waitingRequestIds = model.requests.filter((r) => requestStateAt(r, t) === 'waiting').map((r) => r.id)
  return { t, vehicles, waitingRequestIds, cumulative: countersAt(model, t) }
}

export function nextEventTime(model: ReplayModel, t: number): number {
  return model.eventTimes.find((x) => x > t + 500) ?? model.timelineEnd
}

export function previousEventTime(model: ReplayModel, t: number): number {
  for (let i = model.eventTimes.length - 1; i >= 0; i -= 1) {
    const x = model.eventTimes[i]!
    if (x < t - 500) return x
  }
  return model.windowStart
}

/** Série acumulada para gráficos (amostrada a cada `stepMs`). */
export function cumulativeSeries(model: ReplayModel, stepMs: number): (CumulativeCounters & { t: number })[] {
  const out: (CumulativeCounters & { t: number })[] = []
  for (let t = model.windowStart; t < model.timelineEnd; t += stepMs) out.push({ t, ...countersAt(model, t) })
  out.push({ t: model.timelineEnd, ...countersAt(model, model.timelineEnd) })
  return out
}

/** Histograma de criação de pedidos por intervalo (para a linha do tempo). */
export function requestHistogram(model: ReplayModel, bucketMs: number): number[] {
  const buckets = Math.max(1, Math.ceil((model.windowEnd - model.windowStart) / bucketMs))
  const counts = new Array<number>(buckets).fill(0)
  for (const r of model.requests) {
    const i = Math.min(buckets - 1, Math.floor((r.createdAt - model.windowStart) / bucketMs))
    if (i >= 0) counts[i] = (counts[i] ?? 0) + 1
  }
  return counts
}
