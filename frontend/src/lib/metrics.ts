import type { AlgorithmId, DayResult, ExecutionOutcome, ScenarioMetrics } from '@/types'

/**
 * Redução relativa do KM vazio estimado, em pontos percentuais.
 * Segue `docs/indicadores.md`: `(baseline − proposto) / baseline × 100`, somente com
 * denominador positivo. Positivo = cenário proposto melhor.
 */
export function reductionPercent(baselineKm: number, proposedKm: number): number | null {
  if (!Number.isFinite(baselineKm) || !Number.isFinite(proposedKm) || baselineKm <= 0) return null
  return ((baselineKm - proposedKm) / baselineKm) * 100
}

/** Cobertura do proposto não pode ser inferior à do baseline (com tolerância numérica). */
export function coverageNotWorse(baseline: number | null, proposed: number | null): boolean | null {
  if (baseline === null || proposed === null) return null
  return proposed + 1e-9 >= baseline
}

export const EXECUTION_OUTCOMES: readonly ExecutionOutcome[] = [
  'executed',
  'driver_absent',
  'driver_on_trip',
  'availability_conflict',
]

export function emptyExecution(): Record<ExecutionOutcome, number> {
  return { executed: 0, driver_absent: 0, driver_on_trip: 0, availability_conflict: 0 }
}

type SummableKey =
  | 'requests'
  | 'served'
  | 'unserved'
  | 'pickupKm'
  | 'repositionKm'
  | 'plannedMoves'
  | 'executedMoves'
  | 'plannedRepositionKm'

/** Soma métricas de vários dias do mesmo cenário, recalculando razões a partir dos totais. */
export function aggregateMetrics(items: readonly ScenarioMetrics[]): ScenarioMetrics | null {
  const first = items[0]
  if (!first) return null
  const sum = (key: SummableKey) => items.reduce((acc, m) => acc + m[key], 0)
  const requests = sum('requests')
  const served = sum('served')
  const pickupKm = sum('pickupKm')
  const repositionKm = sum('repositionKm')
  const execution = emptyExecution()
  let waitWeighted = 0
  let waitCount = 0
  for (const m of items) {
    for (const k of EXECUTION_OUTCOMES) execution[k] += m.execution[k]
    if (m.meanWaitMinutes !== null) {
      waitWeighted += m.meanWaitMinutes * m.served
      waitCount += m.served
    }
  }
  const emptyKmTotal = pickupKm + repositionKm
  return {
    algorithmId: first.algorithmId,
    requests,
    served,
    unserved: sum('unserved'),
    coverage: requests > 0 ? served / requests : null,
    pickupKm,
    repositionKm,
    returnKm: null,
    emptyKmTotal,
    emptyKmPerServed: served > 0 ? emptyKmTotal / served : null,
    meanWaitMinutes: waitCount > 0 ? waitWeighted / waitCount : null,
    plannedMoves: sum('plannedMoves'),
    executedMoves: sum('executedMoves'),
    plannedRepositionKm: sum('plannedRepositionKm'),
    execution,
    distanceMethod: first.distanceMethod,
    dataKind: first.dataKind,
    observedKm: null,
  }
}

export interface ScenarioComparison {
  algorithmId: AlgorithmId
  baseline: ScenarioMetrics
  proposed: ScenarioMetrics
  /** Diferença de pickup (baseline − proposto); positiva = pickup economizado. */
  pickupSavingKm: number
  repositionCostKm: number
  /** Efeito líquido = baseline − proposto no KM vazio total; positivo = proposto melhor. */
  netKm: number
  reductionPercent: number | null
  coverageDelta: number | null
  coverageNotWorse: boolean | null
}

export function compareScenario(baseline: ScenarioMetrics, proposed: ScenarioMetrics): ScenarioComparison {
  return {
    algorithmId: proposed.algorithmId,
    baseline,
    proposed,
    pickupSavingKm: baseline.pickupKm - proposed.pickupKm,
    repositionCostKm: proposed.repositionKm,
    netKm: baseline.emptyKmTotal - proposed.emptyKmTotal,
    reductionPercent: reductionPercent(baseline.emptyKmTotal, proposed.emptyKmTotal),
    coverageDelta:
      baseline.coverage !== null && proposed.coverage !== null ? proposed.coverage - baseline.coverage : null,
    coverageNotWorse: coverageNotWorse(baseline.coverage, proposed.coverage),
  }
}

/** Agrega todos os dias por cenário. */
export function aggregateByAlgorithm(
  days: readonly DayResult[],
  algorithms: readonly AlgorithmId[],
): Partial<Record<AlgorithmId, ScenarioMetrics>> {
  const out: Partial<Record<AlgorithmId, ScenarioMetrics>> = {}
  for (const id of algorithms) {
    const agg = aggregateMetrics(days.map((d) => d.metrics[id]))
    if (agg) out[id] = agg
  }
  return out
}

/** Dias em que o cenário não piorou a cobertura (recorte também usado no relatório real). */
export function daysCoverageNotWorse(days: readonly DayResult[], algorithmId: AlgorithmId): DayResult[] {
  return days.filter((d) => coverageNotWorse(d.metrics.baseline.coverage, d.metrics[algorithmId].coverage) === true)
}
