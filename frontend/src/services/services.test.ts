import { describe, expect, it, vi } from 'vitest'
import { createHttpDataSource } from './httpDataSource'
import { createMockDataSource } from './mockDataSource'
import { fromPythonAlgorithm, fromPythonScenarioMetrics, type PythonScenarioMetrics } from './pythonAdapters'
import { DataSourceError } from './dataSource'

describe('mockDataSource', () => {
  const source = createMockDataSource({ delayMs: 0 })

  it('expõe os quatro cenários e marca os dados como fictícios', async () => {
    const [experiments, algorithms] = await Promise.all([source.listExperiments(), source.listAlgorithms()])
    expect(algorithms.map((a) => a.id)).toEqual(['baseline', 'guloso', 'proporcional', 'atribuicao_otima'])
    for (const e of experiments) {
      expect(e.provenance.kind).toBe('demo')
      expect(e.distanceMethod).toBe('haversine')
    }
  })

  it('rejeita experimento ou dia inexistente com erro tipado', async () => {
    await expect(source.getExperimentResults('nao-existe')).rejects.toBeInstanceOf(DataSourceError)
    await expect(source.getDaySnapshot('demo-manha', '2026-09-01')).rejects.toThrow(/fora do experimento/)
  })
})

describe('httpDataSource', () => {
  it('monta as rotas esperadas e propaga status HTTP', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('nope', { status: 503 }))
    vi.stubGlobal('fetch', fetchMock)
    const source = createHttpDataSource('http://api.local/api/')
    await expect(source.getScenarioRun('exp 1', '2030-01-07', 'guloso')).rejects.toMatchObject({ status: 503 })
    expect(fetchMock).toHaveBeenCalledWith(
      'http://api.local/api/experiments/exp%201/days/2030-01-07/scenarios/guloso',
      expect.objectContaining({ headers: { Accept: 'application/json' } }),
    )
    vi.unstubAllGlobals()
  })
})

describe('adaptador do result.json do gold-replay', () => {
  const raw: PythonScenarioMetrics = {
    scenario: 'proposed',
    dataset_kind: 'synthetic',
    distance_method: 'haversine',
    requests: 10,
    served: 9,
    coverage: 0.9,
    estimated_pickup_km: 12,
    estimated_reposition_km: 3,
    estimated_km_dead_total: 15,
    estimated_km_dead_per_served: 15 / 9,
    mean_estimated_wait_minutes: 6,
    observed_km: null,
    return_km: null,
  }

  it('mapeia métricas e desfechos sem inventar KM observado', () => {
    const m = fromPythonScenarioMetrics('guloso', raw, {
      recommendations: 5,
      planned_reposition_km: 7,
      predicted_fleet: 20,
      projected_pickup_saving_km: 9,
      execution: { aplicada: 2, motorista_ausente: 2, motorista_em_corrida: 1 },
    })
    expect(m.emptyKmTotal).toBe(15)
    expect(m.unserved).toBe(1)
    expect(m.execution).toEqual({ executed: 2, driver_absent: 2, driver_on_trip: 1, availability_conflict: 0 })
    expect(m.observedKm).toBeNull()
    expect(m.returnKm).toBeNull()
    expect(m.dataKind).toBe('synthetic')
  })

  it('recusa método de distância diferente (comparabilidade)', () => {
    expect(() => fromPythonScenarioMetrics('guloso', { ...raw, distance_method: 'osrm' }, null)).toThrow(/não suportado/)
  })

  it('traduz nomes de algoritmo conhecidos', () => {
    expect(fromPythonAlgorithm(undefined)).toBe('guloso')
    expect(fromPythonAlgorithm('atribuicao_otima')).toBe('atribuicao_otima')
    expect(fromPythonAlgorithm('busca_local')).toBeNull()
  })
})
