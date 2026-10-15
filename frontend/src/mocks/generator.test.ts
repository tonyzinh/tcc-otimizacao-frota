import { beforeEach, describe, expect, it } from 'vitest'
import { haversineKm } from '@/lib/geo'
import { toEpoch } from '@/lib/time'
import type { SimulationEvent } from '@/types'
import { EXPERIMENTS } from './catalog'
import {
  buildDayWorld,
  buildExperimentResults,
  buildScenarioRun,
  buildSensitivity,
  planDemoMoves,
  resetDemoCaches,
} from './generator'
import { isOnLand } from './geography'
import { createRng } from '@/lib/random'

const experiment = EXPERIMENTS[0]!
const date = experiment.days[0]!

describe('gerador demonstrativo', () => {
  beforeEach(() => resetDemoCaches())

  it('é determinístico para a mesma semente', () => {
    const a = buildScenarioRun(experiment, date, 'guloso')
    resetDemoCaches()
    const b = buildScenarioRun(experiment, date, 'guloso')
    expect(b.metrics).toEqual(a.metrics)
    expect(b.events.length).toBe(a.events.length)
  })

  it('marca a proveniência como demonstrativa e usa identificadores pseudônimos', () => {
    const world = buildDayWorld(experiment, date)
    expect(world.snapshot.provenance.kind).toBe('demo')
    expect(world.snapshot.provenance.disclaimer).toMatch(/fictícios/i)
    for (const v of world.snapshot.vehicles) expect(v.id).toMatch(/^V-\d{2}$/)
    for (const r of world.snapshot.requests) expect(r.id).toMatch(/^R-\d{4}-\d{3}$/)
  })

  it('gera pedidos e frota em terra, dentro da janela avaliada', () => {
    const world = buildDayWorld(experiment, date)
    expect(world.snapshot.requests.length).toBeGreaterThan(40)
    for (const r of world.snapshot.requests) {
      expect(isOnLand(r.origin)).toBe(true)
      const t = toEpoch(r.createdAt)
      expect(t).toBeGreaterThanOrEqual(world.windowStart)
      expect(t).toBeLessThan(world.windowEnd)
    }
    for (const f of world.snapshot.fleetAtStart) expect(isOnLand(f.position)).toBe(true)
  })

  it('mantém o mesmo mundo e a mesma assinatura em todos os cenários do dia', () => {
    const runs = experiment.algorithms.map((id) => buildScenarioRun(experiment, date, id))
    const signatures = new Set(runs.map((r) => r.inputSignature))
    expect(signatures.size).toBe(1)
    const requests = new Set(runs.map((r) => r.metrics.requests))
    expect(requests.size).toBe(1)
  })

  it('não reposiciona no baseline e soma o reposicionamento ao KM vazio dos demais', () => {
    const baseline = buildScenarioRun(experiment, date, 'baseline')
    expect(baseline.movements).toHaveLength(0)
    expect(baseline.metrics.repositionKm).toBe(0)
    for (const id of ['guloso', 'proporcional', 'atribuicao_otima'] as const) {
      const m = buildScenarioRun(experiment, date, id).metrics
      expect(m.emptyKmTotal).toBeCloseTo(m.pickupKm + m.repositionKm, 9)
      expect(m.returnKm).toBeNull()
      expect(m.observedKm).toBeNull()
    }
  })

  it('planeja no corte (D às 20h), antes do horizonte avaliado', () => {
    const world = buildDayWorld(experiment, date)
    const run = buildScenarioRun(experiment, date, 'guloso')
    expect(run.movements.length).toBeGreaterThan(0)
    for (const m of run.movements) {
      expect(toEpoch(m.plannedAt)).toBe(world.cutoff)
      expect(toEpoch(m.plannedAt)).toBeLessThan(world.windowStart)
      if (m.executedStart) expect(toEpoch(m.executedStart)).toBeGreaterThanOrEqual(world.windowStart)
    }
  })

  it('o plano não depende do que foi observado em D+1', () => {
    const world = buildDayWorld(experiment, date)
    const forecast = world.snapshot.zones.map(({ h3, centroid, forecastRides }) => ({ h3, centroid, forecastRides }))
    const profile = { moveFraction: 0.4, focus: 1, distanceScaleKm: 5 }
    const a = planDemoMoves(forecast, world.snapshot.predictedFleet, profile, 12, createRng('x'))
    // Zonas com contagem observada alterada não mudam a entrada do plano (só a previsão entra).
    const tampered = world.snapshot.zones.map((z) => ({ ...z, observedRides: z.observedRides * 10 }))
    const b = planDemoMoves(
      tampered.map(({ h3, centroid, forecastRides }) => ({ h3, centroid, forecastRides })),
      world.snapshot.predictedFleet,
      profile,
      12,
      createRng('x'),
    )
    expect(b).toEqual(a)
  })

  it('respeita o limite de reposicionamento planejado', () => {
    const run = buildScenarioRun(experiment, date, 'guloso', { maxRepositionKm: 3 })
    for (const m of run.movements) expect(m.plannedKm).toBeLessThanOrEqual(3 + 0.3)
  })

  it('nunca ocupa um veículo em dois atendimentos ou movimentos ao mesmo tempo', () => {
    for (const id of experiment.algorithms) {
      const run = buildScenarioRun(experiment, date, id)
      const busy = new Map<string, { start: number; end: number }[]>()
      const open = new Map<string, number>()
      const add = (vehicleId: string, start: number, end: number) => {
        const list = busy.get(vehicleId) ?? []
        list.push({ start, end })
        busy.set(vehicleId, list)
      }
      for (const e of run.events as SimulationEvent[]) {
        if (!e.vehicleId) continue
        const t = toEpoch(e.t)
        if (e.type === 'dispatch' || e.type === 'reposition_start') open.set(e.vehicleId, t)
        if (e.type === 'dropoff' || e.type === 'reposition_end') {
          const start = open.get(e.vehicleId)
          expect(start).toBeDefined()
          add(e.vehicleId, start!, t)
          open.delete(e.vehicleId)
        }
      }
      for (const intervals of busy.values()) {
        intervals.sort((a, b) => a.start - b.start)
        for (let i = 1; i < intervals.length; i += 1) {
          expect(intervals[i]!.start).toBeGreaterThanOrEqual(intervals[i - 1]!.end)
        }
      }
    }
  })

  it('só executa movimentos de veículos presentes e calcula o km a partir da posição real', () => {
    const world = buildDayWorld(experiment, date)
    const run = buildScenarioRun(experiment, date, 'proporcional')
    for (const m of run.movements) {
      const vd = world.vehicleDays.get(m.vehicleId)!
      if (m.outcome === 'executed') {
        expect(vd.present).toBe(true)
        expect(m.executedKm).toBeCloseTo(haversineKm(m.executedFrom!, m.to), 9)
      } else {
        expect(m.executedStart).toBeNull()
      }
      if (!vd.present) expect(m.outcome).toBe('driver_absent')
    }
    const executed = run.movements.filter((m) => m.outcome === 'executed').length
    expect(run.metrics.executedMoves).toBe(executed)
  })

  it('gera resultados por dia e sensibilidade comparáveis', () => {
    const results = buildExperimentResults(experiment)
    expect(results.days).toHaveLength(experiment.days.length)
    for (const d of results.days) {
      expect(d.metrics.baseline.served).toBeLessThanOrEqual(d.metrics.baseline.requests)
      expect(d.observedTotal).toBe(d.metrics.baseline.requests)
    }
    const sensitivity = buildSensitivity(experiment)
    expect(sensitivity.results).toHaveLength(sensitivity.variants.length * 3)
  })
})
