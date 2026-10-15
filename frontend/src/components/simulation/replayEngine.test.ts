import { beforeAll, describe, expect, it } from 'vitest'
import { buildDayWorld, buildScenarioRun, EXPERIMENTS } from '@/mocks'
import type { DaySnapshot, ScenarioRun } from '@/types'
import {
  buildReplayModel,
  countersAt,
  cumulativeSeries,
  frameAt,
  nextEventTime,
  previousEventTime,
  requestStateAt,
  type ReplayModel,
} from './replayEngine'

const experiment = EXPERIMENTS[0]!
const date = experiment.days[2]!
let snapshot: DaySnapshot
let run: ScenarioRun
let model: ReplayModel

beforeAll(() => {
  snapshot = buildDayWorld(experiment, date).snapshot
  run = buildScenarioRun(experiment, date, 'guloso')
  model = buildReplayModel(snapshot, run)
})

describe('motor de replay', () => {
  it('cria uma trilha contínua e sem sobreposição por veículo presente', () => {
    expect(model.tracks.size).toBe(snapshot.fleetAtStart.length)
    for (const segments of model.tracks.values()) {
      expect(segments[0]!.t0).toBe(model.windowStart)
      for (let i = 1; i < segments.length; i += 1) {
        expect(segments[i]!.t0).toBe(segments[i - 1]!.t1)
      }
      expect(segments[segments.length - 1]!.t1).toBe(model.timelineEnd)
    }
  })

  it('cada veículo tem exatamente um estado por instante', () => {
    const t = model.windowStart + 75 * 60_000
    const frame = frameAt(model, t)
    const ids = frame.vehicles.map((v) => v.vehicleId)
    expect(new Set(ids).size).toBe(ids.length)
    expect(ids.length).toBe(snapshot.fleetAtStart.length)
  })

  it('interpola a posição ao longo do segmento', () => {
    const segment = [...model.tracks.values()].flat().find((s) => s.kind === 'repositioning' && s.path.length > 2)!
    expect(segment).toBeDefined()
    const segments = model.tracks.get(segment.vehicleId)!
    const at = (t: number) => frameAt({ ...model, tracks: new Map([[segment.vehicleId, segments]]) }, t).vehicles[0]!
    expect(at(segment.t0).position).toEqual(segment.path[0])
    const mid = at((segment.t0 + segment.t1) / 2)
    expect(mid.state).toBe('repositioning')
    expect(mid.progress).toBeCloseTo(0.5, 2)
  })

  it('acumula KM monotonicamente e fecha com as métricas do cenário', () => {
    const series = cumulativeSeries(model, 5 * 60_000)
    for (let i = 1; i < series.length; i += 1) {
      expect(series[i]!.emptyKm).toBeGreaterThanOrEqual(series[i - 1]!.emptyKm - 1e-9)
    }
    const final = countersAt(model, model.timelineEnd)
    expect(final.pickupKm).toBeCloseTo(run.metrics.pickupKm, 6)
    expect(final.repositionKm).toBeCloseTo(run.metrics.repositionKm, 6)
    expect(final.served).toBe(run.metrics.served)
    expect(final.unserved).toBe(run.metrics.unserved)
    expect(final.pending).toBe(0)
  })

  it('não mostra pedidos antes de serem criados', () => {
    const r = model.requests[model.requests.length - 1]!
    expect(requestStateAt(r, r.createdAt - 1)).toBeNull()
    expect(requestStateAt(r, r.createdAt)).not.toBeNull()
  })

  it('navega entre eventos para frente e para trás', () => {
    const t = model.windowStart + 30 * 60_000
    const next = nextEventTime(model, t)
    const prev = previousEventTime(model, t)
    expect(next).toBeGreaterThan(t)
    expect(prev).toBeLessThan(t)
    expect(model.eventTimes).toContain(next)
  })

  it('o baseline não tem trilhas de reposicionamento', () => {
    const base = buildReplayModel(snapshot, buildScenarioRun(experiment, date, 'baseline'))
    expect(base.trails.some((t) => t.kind === 'repositioning')).toBe(false)
  })
})
