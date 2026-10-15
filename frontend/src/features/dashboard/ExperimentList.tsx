import { ChevronRight } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/cn'
import { formatDay } from '@/lib/format'
import type { Experiment } from '@/types'

export function ExperimentList({
  experiments,
  activeId,
  onSelect,
}: {
  experiments: readonly Experiment[]
  activeId: string | undefined
  onSelect: (id: string) => void
}) {
  return (
    <ul className="divide-y divide-line">
      {experiments.map((e) => {
        const p = e.parameters
        const active = e.id === activeId
        return (
          <li key={e.id}>
            <button
              type="button"
              onClick={() => onSelect(e.id)}
              aria-pressed={active}
              className={cn(
                'group flex w-full cursor-pointer items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-raised',
                active && 'bg-surface-raised',
              )}
            >
              <span className={cn('h-8 w-[3px] shrink-0 rounded-full bg-line-strong', active && 'bg-brand')} aria-hidden />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[13px] font-medium text-fg">{e.name}</span>
                  <Badge size="sm" variant="demo">
                    DEMO
                  </Badge>
                </div>
                <p className="mt-0.5 truncate text-xs text-fg-subtle">
                  {e.days.length} dias ({formatDay(e.days[0] ?? '')} – {formatDay(e.days[e.days.length - 1] ?? '')}) · corte D {p.cutoffHour}h ·
                  reposic. ≤ {p.maxRepositionKm} km · {e.algorithms.length} cenários
                </p>
              </div>
              <ChevronRight className="size-4 text-fg-subtle transition-transform group-hover:translate-x-0.5" aria-hidden />
            </button>
          </li>
        )
      })}
    </ul>
  )
}
