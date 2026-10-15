import { ChevronDown } from 'lucide-react'
import { useId, useState } from 'react'
import { cn } from '@/lib/cn'
import { rgbToHex, type RGB } from '@/theme/colors'

export type LegendSwatch =
  | { kind: 'dot'; color: RGB; ring?: boolean }
  | { kind: 'ring'; color: RGB }
  | { kind: 'line'; color: RGB }
  | { kind: 'dash'; color: RGB }
  | { kind: 'fade'; color: RGB }
  | { kind: 'ramp'; colors: RGB[] }

export interface LegendItem {
  id: string
  label: string
  swatch: LegendSwatch
  hint?: string
}

function Swatch({ swatch }: { swatch: LegendSwatch }) {
  switch (swatch.kind) {
    case 'dot':
      return (
        <span
          className={cn('size-2.5 rounded-full', swatch.ring && 'shadow-[0_0_0_3px_color-mix(in_srgb,currentColor_25%,transparent)]')}
          style={{ background: rgbToHex(swatch.color), color: rgbToHex(swatch.color) }}
        />
      )
    case 'ring':
      return <span className="size-2.5 rounded-full border-[1.5px]" style={{ borderColor: rgbToHex(swatch.color) }} />
    case 'line':
      return <span className="h-[2.5px] w-4 rounded-full" style={{ background: rgbToHex(swatch.color) }} />
    case 'dash':
      return (
        <span
          className="h-[2px] w-4"
          style={{ backgroundImage: `linear-gradient(90deg, ${rgbToHex(swatch.color)} 55%, transparent 55%)`, backgroundSize: '6px 2px' }}
        />
      )
    case 'fade':
      return (
        <span
          className="h-[2.5px] w-4 rounded-full"
          style={{ background: `linear-gradient(90deg, transparent, ${rgbToHex(swatch.color)})` }}
        />
      )
    case 'ramp':
      return (
        <span
          className="h-2 w-6 rounded-[2px]"
          style={{ background: `linear-gradient(90deg, ${swatch.colors.map(rgbToHex).join(', ')})` }}
        />
      )
  }
}

/** Legenda compacta e recolhível: lista só as camadas ativas, sempre com rótulo textual. */
export function MapLegend({
  items,
  title = 'Legenda',
  className,
  defaultOpen = true,
  collapsible = true,
}: {
  items: readonly LegendItem[]
  title?: string
  className?: string
  defaultOpen?: boolean
  collapsible?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  const listId = useId()
  if (items.length === 0) return null
  const expanded = !collapsible || open
  return (
    <div className={cn('glass rounded-lg border border-line px-2.5 py-2 shadow-panel', className)}>
      {collapsible ? (
        <button
          type="button"
          aria-expanded={open}
          aria-controls={listId}
          onClick={() => setOpen((v) => !v)}
          className="flex w-full cursor-pointer items-center justify-between gap-2"
        >
          <span className="eyebrow">{title}</span>
          <ChevronDown className={cn('size-3.5 text-fg-subtle transition-transform', open && 'rotate-180')} aria-hidden />
        </button>
      ) : (
        <div className="eyebrow">{title}</div>
      )}
      {expanded ? (
        <ul id={listId} className="mt-1.5 grid gap-1" aria-label="Legenda do mapa">
          {items.map((item) => (
            <li key={item.id} className="flex items-center gap-2 text-2xs text-fg-muted" title={item.hint}>
              <span className="flex w-6 shrink-0 items-center justify-center">
                <Swatch swatch={item.swatch} />
              </span>
              <span className="truncate">{item.label}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
