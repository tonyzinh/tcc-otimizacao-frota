import type { Experiment } from '@/types'
import { DataSourceError, type FleetLabDataSource } from './dataSource'

/** O gerador (e o h3-js) só é carregado quando o primeiro dado é pedido. */
const loadMocks = () => import('@/mocks')

function findExperiment(experiments: readonly Experiment[], id: string): Experiment {
  const experiment = experiments.find((e) => e.id === id)
  if (!experiment) throw new DataSourceError(`Experimento demonstrativo não encontrado: ${id}`, 404)
  return experiment
}

function assertDay(experiment: Experiment, date: string): void {
  if (!experiment.days.includes(date)) {
    throw new DataSourceError(`Dia ${date} fora do experimento ${experiment.id}`, 404)
  }
}

/** Atraso artificial pequeno para exercitar estados de carregamento sem atrapalhar o uso. */
async function settle<T>(compute: (mocks: Awaited<ReturnType<typeof loadMocks>>) => T, delayMs: number): Promise<T> {
  const mocks = await loadMocks()
  if (delayMs > 0) await new Promise((resolve) => setTimeout(resolve, delayMs))
  return compute(mocks)
}

export function createMockDataSource(options: { delayMs?: number } = {}): FleetLabDataSource {
  const delay = options.delayMs ?? 60
  return {
    kind: 'mock',
    listExperiments: () => settle((m) => m.EXPERIMENTS.map((e) => ({ ...e })), delay),
    listAlgorithms: () => settle((m) => m.ALGORITHMS.map((a) => ({ ...a })), delay),
    getExperimentResults: (experimentId) =>
      settle((m) => m.buildExperimentResults(findExperiment(m.EXPERIMENTS, experimentId)), delay),
    getDaySnapshot: (experimentId, date) =>
      settle((m) => {
        const experiment = findExperiment(m.EXPERIMENTS, experimentId)
        assertDay(experiment, date)
        return m.buildDayWorld(experiment, date).snapshot
      }, delay),
    getScenarioRun: (experimentId, date, algorithmId) =>
      settle((m) => {
        const experiment = findExperiment(m.EXPERIMENTS, experimentId)
        assertDay(experiment, date)
        if (!experiment.algorithms.includes(algorithmId)) {
          throw new DataSourceError(`Algoritmo ${algorithmId} não pertence ao experimento`, 404)
        }
        return m.buildScenarioRun(experiment, date, algorithmId)
      }, delay),
    getSensitivity: (experimentId) => settle((m) => m.buildSensitivity(findExperiment(m.EXPERIMENTS, experimentId)), delay * 2),
  }
}
