import { describe, expect, it } from 'vitest'
import type { DemandZone, RepositionMovement, VehicleFrame } from '@/types'
import { aggregateFlows, countStates, topZoneShare, vehiclesByZone } from './transforms'

const zone = (h3: string, lng: number): DemandZone => ({
  h3,
  centroid: [lng, -20.3],
  locality: h3,
  municipality: 'Vitória',
  forecastRides: 1,
  observedRides: 1,
})

const move = (id: string, from: string, to: string, outcome: RepositionMovement['outcome']): RepositionMovement => ({
  id,
  algorithmId: 'guloso',
  vehicleId: 'V-01',
  plannedFrom: [-40.3, -20.3],
  executedFrom: outcome === 'executed' ? [-40.3, -20.3] : null,
  to: [-40.2, -20.3],
  fromZone: from,
  toZone: to,
  plannedKm: 2,
  executedKm: outcome === 'executed' ? 2.5 : null,
  plannedAt: '2030-01-06T20:00:00-03:00',
  scheduledStart: '2030-01-07T07:00:00-03:00',
  outcome,
  executedStart: null,
  executedEnd: null,
  plannedPath: [],
  executedPath: null,
  pathKind: 'illustrative',
})

describe('aggregateFlows', () => {
  it('agrega por par de zonas e filtra executados', () => {
    const zones = [zone('a', -40.3), zone('b', -40.2)]
    const moves = [move('1', 'a', 'b', 'executed'), move('2', 'a', 'b', 'driver_absent'), move('3', 'b', 'a', 'executed')]
    const planned = aggregateFlows(moves, zones, 'planned')
    expect(planned.find((f) => f.id === 'a>b')).toMatchObject({ count: 2, km: 4 })
    const executed = aggregateFlows(moves, zones, 'executed')
    expect(executed.find((f) => f.id === 'a>b')).toMatchObject({ count: 1, km: 2.5 })
  })
})

describe('concentração (descritivo)', () => {
  const frames: VehicleFrame[] = [
    { vehicleId: '1', position: [-40.3, -20.3], state: 'idle', progress: 0 },
    { vehicleId: '2', position: [-40.3, -20.3], state: 'idle', progress: 0 },
    { vehicleId: '3', position: [-40.2, -20.2], state: 'on_trip', progress: 0.5 },
    { vehicleId: '4', position: [-40.2, -20.2], state: 'unavailable', progress: 0 },
  ]

  it('ignora indisponíveis e conta livres por zona', () => {
    const byZone = vehiclesByZone(frames, 7)
    expect(byZone.reduce((s, z) => s + z.total, 0)).toBe(3)
    expect(topZoneShare(byZone, 1)).toBe(1)
    expect(countStates(frames)).toMatchObject({ idle: 2, on_trip: 1, unavailable: 1 })
  })

  it('não define parcela sem veículos livres', () => {
    expect(topZoneShare([], 5)).toBeNull()
  })
})
