import { useMemo } from 'react'
import { Slider } from '@/components/ui/slider'
import { cn } from '@/lib/cn'
import { formatClock } from '@/lib/format'
import { HOUR } from '@/lib/time'

export interface TimelineMarker {
  t: number
  tone: 'brand' | 'series' | 'muted'
  color?: string
}

/**
 * Linha do tempo com densidade de pedidos (barras), marcadores de reposicionamento e cursor.
 * O controle deslizante é acessível por teclado (setas) via Radix.
 */
export function Timeline({
  start,
  end,
  windowEnd,
  value,
  onChange,
  histogram,
  markers = [],
  stepMs = 15_000,
}: {
  start: number
  end: number
  windowEnd?: number
  value: number
  onChange: (t: number) => void
  histogram?: readonly number[]
  markers?: readonly TimelineMarker[]
  stepMs?: number
}) {
  const span = Math.max(1, end - start)
  const max = useMemo(() => Math.max(1, ...(histogram ?? [0])), [histogram])
  const ticks = useMemo(() => {
    const out: number[] = []
    const first = Math.ceil(start / HOUR) * HOUR
    for (let t = first; t <= end; t += HOUR / 2) out.push(t)
    return out
  }, [start, end])
  const histogramSpan = (windowEnd ?? end) - start

  return (
    <div className="@container relative w-full select-none">
      <div className="relative h-9">
        {histogram ? (
          <div className="absolute inset-x-0 bottom-0 flex h-full items-end gap-px" style={{ width: `${(histogramSpan / span) * 100}%` }} aria-hidden>
            {histogram.map((count, i) => (
              <div
                key={i}
                className="flex-1 rounded-t-[2px] bg-fg-subtle/30"
                style={{ height: `${Math.max(count > 0 ? 8 : 0, (count / max) * 100)}%` }}
              />
            ))}
          </div>
        ) : null}
        {markers.map((m, i) => (
          <span
            key={i}
            aria-hidden
            className="absolute bottom-0 h-2 w-px"
            style={{
              left: `${((m.t - start) / span) * 100}%`,
              background: m.color ?? (m.tone === 'brand' ? 'var(--brand)' : 'var(--text-3)'),
            }}
          />
        ))}
        <span
          aria-hidden
          className="pointer-events-none absolute top-0 bottom-0 w-px bg-fg"
          style={{ left: `${((value - start) / span) * 100}%` }}
        />
      </div>
      <Slider
        thumbLabel="Instante do replay"
        min={start}
        max={end}
        step={stepMs}
        value={[value]}
        onValueChange={(v) => onChange(v[0] ?? start)}
        className="-mt-1"
      />
      <div className="relative mt-0.5 h-4 text-[10px] text-fg-subtle tabular" aria-hidden>
        {ticks.map((t) => (
          <span
            key={t}
            className={cn('absolute -translate-x-1/2', t % HOUR !== 0 && 'hidden @lg:inline')}
            style={{ left: `${((t - start) / span) * 100}%` }}
          >
            {formatClock(t)}
          </span>
        ))}
      </div>
    </div>
  )
}
