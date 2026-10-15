import { ToggleGroup } from 'radix-ui'
import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export interface SegmentOption<T extends string> {
  value: T
  label: ReactNode
  title?: string
}

/** Controle segmentado de escolha única (Radix ToggleGroup), sempre com um valor ativo. */
export function Segmented<T extends string>({
  value,
  onValueChange,
  options,
  label,
  size = 'md',
  className,
}: {
  value: T
  onValueChange: (value: T) => void
  options: readonly SegmentOption<T>[]
  label: string
  size?: 'sm' | 'md'
  className?: string
}) {
  return (
    <ToggleGroup.Root
      type="single"
      value={value}
      onValueChange={(v) => {
        if (v) onValueChange(v as T)
      }}
      aria-label={label}
      className={cn('inline-flex items-center gap-0.5 rounded-lg border border-line bg-surface-raised p-0.5', className)}
    >
      {options.map((o) => (
        <ToggleGroup.Item
          key={o.value}
          value={o.value}
          title={o.title}
          className={cn(
            'inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-md font-medium whitespace-nowrap text-fg-subtle transition-colors hover:text-fg data-[state=on]:bg-surface-active data-[state=on]:text-fg data-[state=on]:shadow-[inset_0_0_0_1px_var(--border)] [&_svg]:size-3.5',
            size === 'sm' ? 'h-6 px-2 text-2xs' : 'h-7 px-2.5 text-xs',
          )}
        >
          {o.label}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  )
}
