import { useMemo } from 'react'
import { buildReplayModel, type ReplayModel } from '@/components/simulation/replayEngine'
import { useDataSource, useResource } from '@/services'
import type { AlgorithmId, DaySnapshot, ExperimentResults, ScenarioRun, SensitivityAnalysis } from '@/types'

/** Hooks de leitura: os componentes visuais nunca sabem se os dados vêm do mock ou da API. */
export function useExperimentResults(experimentId: string | undefined) {
  const source = useDataSource()
  return useResource<ExperimentResults>(experimentId ? `${source.kind}:results:${experimentId}` : null, () =>
    source.getExperimentResults(experimentId!),
  )
}

export function useDaySnapshot(experimentId: string | undefined, date: string | null) {
  const source = useDataSource()
  return useResource<DaySnapshot>(experimentId && date ? `${source.kind}:day:${experimentId}:${date}` : null, () =>
    source.getDaySnapshot(experimentId!, date!),
  )
}

export function useScenarioRun(experimentId: string | undefined, date: string | null, algorithmId: AlgorithmId) {
  const source = useDataSource()
  return useResource<ScenarioRun>(
    experimentId && date ? `${source.kind}:run:${experimentId}:${date}:${algorithmId}` : null,
    () => source.getScenarioRun(experimentId!, date!, algorithmId),
  )
}

export function useSensitivity(experimentId: string | undefined) {
  const source = useDataSource()
  return useResource<SensitivityAnalysis>(experimentId ? `${source.kind}:sensitivity:${experimentId}` : null, () =>
    source.getSensitivity(experimentId!),
  )
}

/** Modelo de replay derivado (só quando dia e cenário pertencem ao mesmo recorte). */
export function useReplayModel(snapshot: DaySnapshot | undefined, run: ScenarioRun | undefined): ReplayModel | null {
  return useMemo(() => {
    if (!snapshot || !run || snapshot.date !== run.date || snapshot.experimentId !== run.experimentId) return null
    return buildReplayModel(snapshot, run)
  }, [snapshot, run])
}
