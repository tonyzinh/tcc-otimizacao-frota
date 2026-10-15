import { FloatingPanel } from '@/components/ui/panel'
import { AlgorithmTag } from '@/features/shared/AlgorithmTag'
import { cn } from '@/lib/cn'
import { formatKm, formatNumber, formatPercent } from '@/lib/format'
import type { AlgorithmId, CumulativeCounters, ScenarioMetrics } from '@/types'

function Stat({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="min-w-0">
      <div className="text-[10px] text-fg-subtle">{label}</div>
      <div className={cn('truncate text-xs tabular', strong ? 'font-semibold text-fg' : 'text-fg-muted')}>{value}</div>
    </div>
  )
}

/** Cabeçalho flutuante de um mapa da comparação: dia inteiro + acumulado até o instante. */
export function ScenarioOverlay({
  algorithmId,
  name,
  metrics,
  counters,
  concentration,
  className,
}: {
  algorithmId: AlgorithmId
  name: string
  metrics: ScenarioMetrics
  counters: CumulativeCounters
  concentration: number | null
  className?: string
}) {
  return (
    <FloatingPanel className={cn('px-3 py-2.5', className)}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <AlgorithmTag id={algorithmId} name={name} className="text-[13px] font-medium text-fg" />
        <span className="text-[10px] text-fg-subtle">dia inteiro</span>
      </div>
      <div className="grid grid-cols-4 gap-3">
        <Stat label="KM vazio" value={formatKm(metrics.emptyKmTotal, 0)} strong />
        <Stat label="Pickup" value={formatKm(metrics.pickupKm, 0)} />
        <Stat label="Reposic." value={formatKm(metrics.repositionKm, 0)} />
        <Stat label="Cobertura" value={formatPercent(metrics.coverage, 1)} />
      </div>
      <div className="mt-2 grid grid-cols-4 gap-3 border-t border-line pt-2">
        <Stat label="Até agora" value={formatKm(counters.emptyKm, 1)} />
        <Stat label="Atendidas" value={formatNumber(counters.served)} />
        <Stat label="Movimentos" value={`${formatNumber(metrics.executedMoves)}/${formatNumber(metrics.plannedMoves)}`} />
        <Stat label="Top 5 zonas" value={concentration === null ? '—' : formatPercent(concentration, 0)} />
      </div>
    </FloatingPanel>
  )
}
