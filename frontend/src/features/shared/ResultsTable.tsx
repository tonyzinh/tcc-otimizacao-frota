import { CircleCheck, CircleX } from 'lucide-react'
import { cn } from '@/lib/cn'
import { formatKm, formatNumber, formatPercent, formatSignedPercent, formatSignedPoints } from '@/lib/format'
import { compareScenario, daysCoverageNotWorse } from '@/lib/metrics'
import type { AlgorithmId, DayResult, ScenarioMetrics } from '@/types'
import { AlgorithmTag } from './AlgorithmTag'

function toneClass(value: number | null, positiveIsGood: boolean): string {
  if (value === null || Math.abs(value) < 1e-9) return 'text-fg-muted'
  return value > 0 === positiveIsGood ? 'text-success-text' : 'text-critical-text'
}

/**
 * Tabela comparativa. A redução segue `docs/indicadores.md` (positivo = proposto melhor) e só
 * existe com baseline positivo. A cobertura é métrica de controle, sempre ao lado do KM.
 */
export function ResultsTable({
  days,
  aggregated,
  algorithms,
  names,
  highlight,
  onSelect,
}: {
  days: readonly DayResult[]
  aggregated: Partial<Record<AlgorithmId, ScenarioMetrics>>
  algorithms: readonly AlgorithmId[]
  names: Record<AlgorithmId, string>
  highlight?: AlgorithmId | null
  onSelect?: (id: AlgorithmId) => void
}) {
  const baseline = aggregated.baseline
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[680px] border-collapse text-[13px] whitespace-nowrap">
        <caption className="sr-only">Resultados agregados por estratégia, KM vazio estimado</caption>
        <thead>
          <tr className="border-b border-line text-left">
            {['Estratégia', 'KM vazio', 'Pickup', 'Reposic.', 'Redução', 'Cobertura', 'Δ cob.', 'Dias ok', 'Execução'].map((h, i) => (
              <th
                key={h}
                scope="col"
                title={h === 'Dias ok' ? 'Dias sem piora de cobertura' : h === 'Δ cob.' ? 'Variação da cobertura vs baseline' : undefined}
                className={cn('eyebrow px-2.5 py-2 font-medium', i > 0 && 'text-right')}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {algorithms.map((id) => {
            const m = aggregated[id]
            if (!m) return null
            const cmp = baseline && id !== 'baseline' ? compareScenario(baseline, m) : null
            const okDays = id === 'baseline' ? null : daysCoverageNotWorse(days, id).length
            const clickable = Boolean(onSelect)
            return (
              <tr
                key={id}
                onClick={clickable ? () => onSelect?.(id) : undefined}
                className={cn(
                  'border-b border-line last:border-b-0 tabular',
                  clickable && 'cursor-pointer hover:bg-surface-raised',
                  highlight === id && 'bg-surface-raised',
                )}
              >
                <th scope="row" className="px-2.5 py-2.5 text-left font-medium text-fg">
                  <AlgorithmTag id={id} name={names[id]} />
                </th>
                <td className="px-2.5 py-2.5 text-right text-fg">{formatKm(m.emptyKmTotal, 0)}</td>
                <td className="px-2.5 py-2.5 text-right text-fg-muted">{formatKm(m.pickupKm, 0)}</td>
                <td className="px-2.5 py-2.5 text-right text-fg-muted">{formatKm(m.repositionKm, 0)}</td>
                <td className={cn('px-2.5 py-2.5 text-right font-medium', toneClass(cmp?.reductionPercent ?? null, true))}>
                  {cmp ? formatSignedPercent(cmp.reductionPercent) : <span className="text-fg-subtle">referência</span>}
                </td>
                <td className="px-2.5 py-2.5 text-right text-fg">{formatPercent(m.coverage)}</td>
                <td className={cn('px-2.5 py-2.5 text-right', toneClass(cmp?.coverageDelta ?? null, true))}>
                  {cmp ? formatSignedPoints(cmp.coverageDelta) : '—'}
                </td>
                <td className="px-2.5 py-2.5 text-right text-fg-muted">
                  {okDays === null ? '—' : `${okDays}/${days.length}`}
                </td>
                <td className="px-2.5 py-2.5 text-right text-fg-muted">
                  {id === 'baseline' ? (
                    '—'
                  ) : (
                    <span className="inline-flex items-center gap-1">
                      {m.executedMoves > 0 ? (
                        <CircleCheck className="size-3.5 text-fg-subtle" aria-hidden />
                      ) : (
                        <CircleX className="size-3.5 text-fg-subtle" aria-hidden />
                      )}
                      {formatNumber(m.executedMoves)}/{formatNumber(m.plannedMoves)}
                    </span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
