import { Suspense } from 'react'
import { FleetMap, type FleetMapProps } from '@/components/maps'
import { Skeleton } from '@/components/ui/feedback'
import { cn } from '@/lib/cn'

/** Mapa com carregamento sob demanda e esqueleto enquanto MapLibre/deck.gl chegam. */
export function MapFrame(props: FleetMapProps) {
  return (
    <Suspense
      fallback={
        <div className={cn('relative overflow-hidden bg-surface', props.className)}>
          <Skeleton className="absolute inset-0 rounded-none opacity-40" />
          <span className="absolute inset-0 flex items-center justify-center text-xs text-fg-subtle">Carregando mapa…</span>
        </div>
      }
    >
      <FleetMap {...props} />
    </Suspense>
  )
}
