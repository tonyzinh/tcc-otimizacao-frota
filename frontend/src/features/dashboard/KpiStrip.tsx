import { Delta, Metric } from '@/components/ui/metric'
import { AlgorithmSwatch } from '@/features/shared/AlgorithmTag'
import { formatKm, formatNumber, formatPercent, formatSignedPercent } from '@/lib/format'
import { compareScenario, type ScenarioComparison } from '@/lib/metrics'
import type { AlgorithmId, ExperimentResults, ProposedAlgorithmId, ScenarioMetrics } from '@/types'

export function KpiStrip({
  results,
  aggregated,
  algorithms,
  names,
}: {
  results: ExperimentResults
  aggregated: Partial<Record<AlgorithmId, ScenarioMetrics>>
  algorithms: readonly AlgorithmId[]
  names: Record<AlgorithmId, string>
}) {
  const baseline = aggregated.baseline
  const observed = results.days.reduce((s, d) => s + d.observedTotal, 0)
  const forecast = results.days.reduce((s, d) => s + d.forecastTotal, 0)
  const comparisons = algorithms
    .filter((id): id is ProposedAlgorithmId => id !== 'baseline')
    .map((id) => (baseline && aggregated[id] ? compareScenario(baseline, aggregated[id]) : null))
    .filter((c): c is ScenarioComparison => c !== null)
  const best = [...comparisons].sort((a, b) => (b.reductionPercent ?? -Infinity) - (a.reductionPercent ?? -Infinity))[0]
  const planned = comparisons.reduce((s, c) => s + c.proposed.plannedMoves, 0)
  const executed = comparisons.reduce((s, c) => s + c.proposed.executedMoves, 0)

  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line lg:grid-cols-5">
      <div className="bg-surface p-4">
        <Metric
          label="Pedidos no período"
          value={formatNumber(observed)}
          context={`previstos no corte: ${formatNumber(forecast, 0)}`}
        />
      </div>
      <div className="bg-surface p-4">
        <Metric
          label="Cobertura · baseline"
          value={formatPercent(baseline?.coverage ?? null)}
          context="métrica de controle"
          accent={<AlgorithmSwatch id="baseline" />}
        />
      </div>
      <div className="bg-surface p-4">
        <Metric
          label="KM vazio · baseline"
          value={formatNumber(baseline?.emptyKmTotal ?? 0)}
          unit="km"
          context="pickup, Haversine estimado"
        />
      </div>
      <div className="bg-surface p-4">
        <Metric
          label="Melhor resultado"
          value={best ? formatSignedPercent(best.reductionPercent) : '—'}
          accent={best ? <AlgorithmSwatch id={best.algorithmId} /> : undefined}
          delta={
            best ? (
              <Delta
                tone={(best.reductionPercent ?? 0) > 0 ? 'good' : 'bad'}
                direction={(best.reductionPercent ?? 0) > 0 ? 'down' : 'up'}
                value={(best.reductionPercent ?? 0) > 0 ? 'reduziu' : 'nenhuma reduziu'}
              />
            ) : undefined
          }
          context={best ? names[best.algorithmId] : undefined}
        />
      </div>
      <div className="col-span-2 bg-surface p-4 lg:col-span-1">
        <Metric
          label="Recomendações executadas"
          value={planned > 0 ? formatPercent(executed / planned, 0) : '—'}
          context={`${formatNumber(executed)} de ${formatNumber(planned)} · ${formatKm(comparisons.reduce((s, c) => s + c.repositionCostKm, 0), 0)} reposic.`}
        />
      </div>
    </div>
  )
}
