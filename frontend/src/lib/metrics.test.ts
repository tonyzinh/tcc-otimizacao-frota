import { describe, expect, it } from 'vitest'
import type { ScenarioMetrics } from '@/types'
import { aggregateMetrics, compareScenario, coverageNotWorse, emptyExecution, reductionPercent } from './metrics'
import { formatSignedPercent, formatSignedPoints } from './format'

function metrics(partial: Partial<ScenarioMetrics>): ScenarioMetrics {
  const pickupKm = partial.pickupKm ?? 0
  const repositionKm = partial.repositionKm ?? 0
  return {
    algorithmId: 'guloso',
    requests: 10,
    served: 10,
    unserved: 0,
    coverage: 1,
    pickupKm,
    repositionKm,
    returnKm: null,
    emptyKmTotal: pickupKm + repositionKm,
    emptyKmPerServed: null,
    meanWaitMinutes: 5,
    plannedMoves: 0,
    executedMoves: 0,
    plannedRepositionKm: 0,
    execution: emptyExecution(),
    distanceMethod: 'haversine',
    dataKind: 'demo',
    observedKm: null,
    ...partial,
  }
}

describe('reductionPercent', () => {
  it('segue (baseline − proposto) / baseline × 100', () => {
    expect(reductionPercent(100, 80)).toBeCloseTo(20)
    expect(reductionPercent(100, 114.6)).toBeCloseTo(-14.6)
  })

  it('não existe sem denominador positivo', () => {
    expect(reductionPercent(0, 10)).toBeNull()
    expect(reductionPercent(-5, 10)).toBeNull()
    expect(reductionPercent(Number.NaN, 10)).toBeNull()
  })
})

describe('compareScenario', () => {
  it('soma o reposicionamento no KM vazio do cenário proposto', () => {
    const baseline = metrics({ algorithmId: 'baseline', pickupKm: 14.757861 })
    // Caso do relatório sintético: pickup economizado igual ao reposicionamento → 0,0%.
    const proposed = metrics({ pickupKm: 11.33133, repositionKm: 3.426531 })
    const cmp = compareScenario(baseline, proposed)
    expect(cmp.pickupSavingKm).toBeCloseTo(3.426531, 6)
    expect(cmp.repositionCostKm).toBeCloseTo(3.426531, 6)
    expect(cmp.netKm).toBeCloseTo(0, 6)
    expect(cmp.reductionPercent).toBeCloseTo(0, 6)
  })

  it('marca piora de cobertura', () => {
    const cmp = compareScenario(metrics({ coverage: 0.933 }), metrics({ coverage: 0.924 }))
    expect(cmp.coverageNotWorse).toBe(false)
    expect(cmp.coverageDelta).toBeCloseTo(-0.009)
  })
})

describe('coverageNotWorse', () => {
  it('é nulo sem cobertura', () => {
    expect(coverageNotWorse(null, 0.9)).toBeNull()
    expect(coverageNotWorse(0.9, 0.9)).toBe(true)
  })
})

describe('aggregateMetrics', () => {
  it('recalcula razões a partir dos totais, não pela média das razões', () => {
    const a = metrics({ requests: 10, served: 10, coverage: 1, pickupKm: 10 })
    const b = metrics({ requests: 30, served: 15, unserved: 15, coverage: 0.5, pickupKm: 20 })
    const agg = aggregateMetrics([a, b])!
    expect(agg.coverage).toBeCloseTo(25 / 40)
    expect(agg.emptyKmTotal).toBeCloseTo(30)
    expect(agg.returnKm).toBeNull()
  })

  it('devolve nulo para lista vazia', () => {
    expect(aggregateMetrics([])).toBeNull()
  })
})

describe('formatação com sinal', () => {
  it('usa sinal explícito e vírgula decimal', () => {
    expect(formatSignedPercent(-14.6)).toBe('−14,6%')
    expect(formatSignedPercent(4.25)).toBe('+4,3%')
    expect(formatSignedPercent(null)).toBe('—')
    expect(formatSignedPoints(0.012)).toBe('+1,2 p.p.')
  })
})
