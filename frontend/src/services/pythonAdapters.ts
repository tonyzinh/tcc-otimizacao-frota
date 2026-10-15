/**
 * Adaptadores do formato produzido por `tcc-frota gold-replay` (result.json) para os contratos do
 * FleetLab. Somente os campos cujos nomes foram conferidos no repositório estão mapeados; o
 * restante fica para quando a API Python existir. Nenhum dado real é lido pelo frontend hoje.
 */
import { emptyExecution } from '@/lib/metrics'
import type { AlgorithmId, DataKind, ExecutionOutcome, ScenarioMetrics } from '@/types'

/** Métricas de um cenário (`days[].baseline` / `days[].proposed`) no result.json. */
export interface PythonScenarioMetrics {
  scenario: string
  dataset_kind: string
  distance_method: string
  requests: number
  served: number
  coverage: number | null
  estimated_pickup_km: number
  estimated_reposition_km: number
  estimated_km_dead_total: number
  estimated_km_dead_per_served: number | null
  mean_estimated_wait_minutes: number | null
  observed_km: null
  return_km: null
}

/** Bloco `days[].plan` no result.json. */
export interface PythonPlanSummary {
  recommendations: number
  planned_reposition_km: number
  predicted_fleet: number
  projected_pickup_saving_km: number
  execution: Partial<Record<'aplicada' | 'motorista_ausente' | 'motorista_em_corrida' | 'conflito_disponibilidade', number>>
}

const EXECUTION_KEYS: Record<keyof PythonPlanSummary['execution'], ExecutionOutcome> = {
  aplicada: 'executed',
  motorista_ausente: 'driver_absent',
  motorista_em_corrida: 'driver_on_trip',
  conflito_disponibilidade: 'availability_conflict',
}

function toDataKind(raw: string): DataKind {
  if (raw === 'synthetic') return 'synthetic'
  if (raw === 'demo') return 'demo'
  return 'real'
}

export function fromPythonScenarioMetrics(
  algorithmId: AlgorithmId,
  raw: PythonScenarioMetrics,
  plan: PythonPlanSummary | null,
): ScenarioMetrics {
  if (raw.distance_method && !raw.distance_method.toLowerCase().includes('haversine')) {
    // O FleetLab só compara KM do mesmo método; outro método exigiria nova decisão (RN028).
    throw new Error(`Método de distância não suportado: ${raw.distance_method}`)
  }
  const execution = emptyExecution()
  if (plan) {
    for (const [key, outcome] of Object.entries(EXECUTION_KEYS) as [keyof typeof EXECUTION_KEYS, ExecutionOutcome][]) {
      execution[outcome] = plan.execution[key] ?? 0
    }
  }
  const pickupKm = raw.estimated_pickup_km
  const repositionKm = raw.estimated_reposition_km
  return {
    algorithmId,
    requests: raw.requests,
    served: raw.served,
    unserved: raw.requests - raw.served,
    coverage: raw.coverage,
    pickupKm,
    repositionKm,
    returnKm: null,
    emptyKmTotal: raw.estimated_km_dead_total,
    emptyKmPerServed: raw.estimated_km_dead_per_served,
    meanWaitMinutes: raw.mean_estimated_wait_minutes,
    plannedMoves: plan?.recommendations ?? 0,
    executedMoves: execution.executed,
    plannedRepositionKm: plan?.planned_reposition_km ?? 0,
    execution,
    distanceMethod: 'haversine',
    dataKind: toDataKind(raw.dataset_kind),
    observedKm: null,
  }
}

/** Nome do algoritmo no `config.algorithm` do result.json → id do FleetLab. */
export function fromPythonAlgorithm(raw: string | undefined): AlgorithmId | null {
  switch (raw ?? 'guloso') {
    case 'guloso':
      return 'guloso'
    case 'proporcional':
      return 'proporcional'
    case 'atribuicao_otima':
      return 'atribuicao_otima'
    default:
      return null
  }
}
