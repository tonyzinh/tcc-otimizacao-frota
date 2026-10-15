/**
 * Transformações de dados → estruturas visuais (sem deck.gl). Mantidas separadas das camadas para
 * serem testáveis e reaproveitadas por painéis e legendas.
 */
import { latLngToCell } from 'h3-js'
import type { DemandZone, LngLat, RepositionMovement, VehicleFrame, VehicleState } from '@/types'
import type { RequestDisplayState, RequestTimeline } from '@/components/simulation/replayEngine'
import { requestStateAt } from '@/components/simulation/replayEngine'

export interface ZoneFlow {
  id: string
  fromZone: string
  toZone: string
  from: LngLat
  to: LngLat
  count: number
  km: number
}

/** Agrega movimentos (executados ou planejados) por par de zonas H3. */
export function aggregateFlows(
  movements: readonly RepositionMovement[],
  zones: readonly DemandZone[],
  mode: 'executed' | 'planned',
): ZoneFlow[] {
  const centroids = new Map(zones.map((z) => [z.h3, z.centroid]))
  const flows = new Map<string, ZoneFlow>()
  for (const m of movements) {
    if (mode === 'executed' && m.outcome !== 'executed') continue
    const key = `${m.fromZone}>${m.toZone}`
    const from = centroids.get(m.fromZone) ?? (mode === 'executed' ? (m.executedFrom ?? m.plannedFrom) : m.plannedFrom)
    const to = centroids.get(m.toZone) ?? m.to
    const km = mode === 'executed' ? (m.executedKm ?? 0) : m.plannedKm
    const flow = flows.get(key)
    if (flow) {
      flow.count += 1
      flow.km += km
    } else {
      flows.set(key, { id: key, fromZone: m.fromZone, toZone: m.toZone, from, to, count: 1, km })
    }
  }
  return [...flows.values()].sort((a, b) => b.count - a.count)
}

export interface VisibleRequest {
  request: RequestTimeline
  state: RequestDisplayState
}

export function visibleRequests(
  requests: readonly RequestTimeline[],
  t: number,
  states: ReadonlySet<RequestDisplayState>,
): VisibleRequest[] {
  const out: VisibleRequest[] = []
  for (const request of requests) {
    const state = requestStateAt(request, t)
    if (state && states.has(state)) out.push({ request, state })
  }
  return out
}

export interface ZoneConcentration {
  h3: string
  idle: number
  total: number
}

/**
 * Descritivo visual: quantos veículos (livres e no total) estão em cada zona num instante.
 * Não é indicador científico do TCC.
 */
export function vehiclesByZone(frames: readonly VehicleFrame[], resolution: number): ZoneConcentration[] {
  const byZone = new Map<string, ZoneConcentration>()
  for (const f of frames) {
    if (f.state === 'unavailable') continue
    const h3 = latLngToCell(f.position[1], f.position[0], resolution)
    const entry = byZone.get(h3) ?? { h3, idle: 0, total: 0 }
    entry.total += 1
    if (f.state === 'idle') entry.idle += 1
    byZone.set(h3, entry)
  }
  return [...byZone.values()].sort((a, b) => b.total - a.total)
}

/** Parcela dos veículos livres concentrada nas `k` zonas com mais veículos livres. */
export function topZoneShare(concentration: readonly ZoneConcentration[], k: number): number | null {
  const idle = concentration.map((z) => z.idle).sort((a, b) => b - a)
  const total = idle.reduce((s, v) => s + v, 0)
  if (total === 0) return null
  return idle.slice(0, k).reduce((s, v) => s + v, 0) / total
}

export function countStates(frames: readonly VehicleFrame[]): Record<VehicleState, number> {
  const out: Record<VehicleState, number> = { idle: 0, repositioning: 0, to_pickup: 0, on_trip: 0, unavailable: 0 }
  for (const f of frames) out[f.state] += 1
  return out
}
