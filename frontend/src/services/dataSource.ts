import type {
  Algorithm,
  AlgorithmId,
  DaySnapshot,
  Experiment,
  ExperimentResults,
  ISODate,
  ScenarioRun,
  SensitivityAnalysis,
} from '@/types'

/**
 * Porta de dados do FleetLab. Os componentes visuais dependem só desta interface; a origem
 * (mocks locais hoje, API Python amanhã) é escolhida em `services/index.ts`.
 */
export interface FleetLabDataSource {
  readonly kind: 'mock' | 'http'
  listExperiments(): Promise<Experiment[]>
  listAlgorithms(): Promise<Algorithm[]>
  getExperimentResults(experimentId: string): Promise<ExperimentResults>
  getDaySnapshot(experimentId: string, date: ISODate): Promise<DaySnapshot>
  getScenarioRun(experimentId: string, date: ISODate, algorithmId: AlgorithmId): Promise<ScenarioRun>
  getSensitivity(experimentId: string): Promise<SensitivityAnalysis>
}

export class DataSourceError extends Error {
  readonly status: number | null

  constructor(message: string, status: number | null = null) {
    super(message)
    this.name = 'DataSourceError'
    this.status = status
  }
}
