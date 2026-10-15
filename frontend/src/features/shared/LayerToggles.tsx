import type { ReactNode } from 'react'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/cn'

export interface LayerToggleItem<K extends string> {
  key: K
  label: string
  hint?: string
  icon?: ReactNode
  disabled?: boolean
}

/** Lista de camadas com interruptores reais (estado controlado pelo chamador). */
export function LayerToggles<K extends string>({
  items,
  value,
  onChange,
  className,
}: {
  items: readonly LayerToggleItem<K>[]
  value: Record<K, boolean>
  onChange: (key: K, enabled: boolean) => void
  className?: string
}) {
  return (
    <ul className={cn('grid gap-0.5', className)}>
      {items.map((item) => {
        const id = `layer-${item.key}`
        return (
          <li key={item.key}>
            <label
              htmlFor={id}
              className={cn(
                'flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 transition-colors hover:bg-surface-raised',
                item.disabled && 'cursor-not-allowed opacity-50',
              )}
              title={item.hint}
            >
              <span className="flex size-4 shrink-0 items-center justify-center text-fg-subtle [&_svg]:size-3.5">{item.icon}</span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs text-fg">{item.label}</span>
                {item.hint ? <span className="block truncate text-[10.5px] text-fg-subtle">{item.hint}</span> : null}
              </span>
              <Switch id={id} checked={value[item.key]} disabled={item.disabled} onCheckedChange={(v) => onChange(item.key, v)} />
            </label>
          </li>
        )
      })}
    </ul>
  )
}

/** Chips de filtro multi-seleção (estados de veículo, desfechos etc.). */
export function FilterChips<K extends string>({
  options,
  selected,
  onToggle,
  label,
}: {
  options: readonly { key: K; label: string; swatch?: ReactNode }[]
  selected: ReadonlySet<K>
  onToggle: (key: K) => void
  label: string
}) {
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-1">
      {options.map((o) => {
        const on = selected.has(o.key)
        return (
          <button
            key={o.key}
            type="button"
            aria-pressed={on}
            onClick={() => onToggle(o.key)}
            className={cn(
              'inline-flex h-6 cursor-pointer items-center gap-1.5 rounded-md border px-2 text-2xs transition-colors',
              on ? 'border-line-strong bg-surface-active text-fg' : 'border-line text-fg-subtle hover:text-fg-muted',
            )}
          >
            {o.swatch}
            {o.label}
          </button>
        )
      })}
    </div>
  )
}
