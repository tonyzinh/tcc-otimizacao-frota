import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { useDataSource, useResource } from '@/services'
import type { Algorithm, AlgorithmId, Experiment, ISODate } from '@/types'

interface ExperimentContextValue {
  experiments: Experiment[]
  algorithms: Algorithm[]
  experiment: Experiment | null
  date: ISODate | null
  setExperimentId: (id: string) => void
  setDate: (date: ISODate) => void
  names: Record<AlgorithmId, string>
  shortNames: Record<AlgorithmId, string>
  loading: boolean
  error: Error | null
}

const ExperimentContext = createContext<ExperimentContextValue | null>(null)

const FALLBACK_NAMES: Record<AlgorithmId, string> = {
  baseline: 'Baseline',
  guloso: 'Guloso (DT001)',
  proporcional: 'Proporcional',
  atribuicao_otima: 'Atribuição ótima',
}

/** Seleção global de experimento e dia, compartilhada entre as páginas. */
export function ExperimentProvider({ children }: { children: ReactNode }) {
  const source = useDataSource()
  const experimentsRes = useResource(`${source.kind}:experiments`, () => source.listExperiments())
  const algorithmsRes = useResource(`${source.kind}:algorithms`, () => source.listAlgorithms())
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedDate, setSelectedDate] = useState<ISODate | null>(null)

  const experiments = useMemo(() => experimentsRes.data ?? [], [experimentsRes.data])
  const algorithms = useMemo(() => algorithmsRes.data ?? [], [algorithmsRes.data])
  const experiment = experiments.find((e) => e.id === selectedId) ?? experiments[0] ?? null
  const date = experiment ? (selectedDate && experiment.days.includes(selectedDate) ? selectedDate : (experiment.days[0] ?? null)) : null

  const names = useMemo(() => {
    const out = { ...FALLBACK_NAMES }
    for (const a of algorithms) out[a.id] = a.name
    return out
  }, [algorithms])
  const shortNames = useMemo(() => {
    const out = { ...FALLBACK_NAMES }
    for (const a of algorithms) out[a.id] = a.shortName
    return out
  }, [algorithms])

  const setExperimentId = useCallback((id: string) => setSelectedId(id), [])
  const setDate = useCallback((d: ISODate) => setSelectedDate(d), [])

  const value = useMemo<ExperimentContextValue>(
    () => ({
      experiments,
      algorithms,
      experiment,
      date,
      setExperimentId,
      setDate,
      names,
      shortNames,
      loading: experimentsRes.loading || algorithmsRes.loading,
      error: experimentsRes.error ?? algorithmsRes.error,
    }),
    [experiments, algorithms, experiment, date, setExperimentId, setDate, names, shortNames, experimentsRes.loading, algorithmsRes.loading, experimentsRes.error, algorithmsRes.error],
  )

  return <ExperimentContext.Provider value={value}>{children}</ExperimentContext.Provider>
}

export function useExperimentContext(): ExperimentContextValue {
  const ctx = useContext(ExperimentContext)
  if (!ctx) throw new Error('useExperimentContext precisa de <ExperimentProvider>')
  return ctx
}
