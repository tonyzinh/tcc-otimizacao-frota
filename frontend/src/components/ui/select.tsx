import { Check, ChevronDown } from 'lucide-react'
import { Select as SelectPrimitive } from 'radix-ui'
import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export interface SelectOption<T extends string> {
  value: T
  label: ReactNode
  hint?: ReactNode
  leading?: ReactNode
}

interface SelectProps<T extends string> {
  value: T
  onValueChange: (value: T) => void
  options: readonly SelectOption<T>[]
  label: string
  className?: string
  triggerClassName?: string
  size?: 'sm' | 'md'
  disabled?: boolean
}

/** Select acessível (Radix) com rótulo para leitores de tela. */
export function Select<T extends string>({
  value,
  onValueChange,
  options,
  label,
  className,
  triggerClassName,
  size = 'md',
  disabled,
}: SelectProps<T>) {
  const current = options.find((o) => o.value === value)
  return (
    <SelectPrimitive.Root value={value} onValueChange={(v) => onValueChange(v as T)} disabled={disabled}>
      <SelectPrimitive.Trigger
        aria-label={label}
        className={cn(
          'group inline-flex min-w-0 cursor-pointer items-center justify-between gap-2 rounded-md border border-line bg-surface-raised text-left text-fg transition-colors hover:border-line-strong data-[state=open]:border-line-strong disabled:opacity-50',
          size === 'sm' ? 'h-7 px-2 text-xs' : 'h-8 px-2.5 text-[13px]',
          triggerClassName,
          className,
        )}
      >
        <span className="flex min-w-0 items-center gap-2 truncate">
          {current?.leading}
          <SelectPrimitive.Value>
            <span className="truncate">{current?.label}</span>
          </SelectPrimitive.Value>
        </span>
        <SelectPrimitive.Icon>
          <ChevronDown className="size-3.5 text-fg-subtle transition-transform group-data-[state=open]:rotate-180" />
        </SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content
          position="popper"
          sideOffset={6}
          className="z-50 max-h-[min(var(--radix-select-content-available-height),360px)] min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-lg border border-line-strong bg-surface-raised p-1 shadow-panel"
        >
          <SelectPrimitive.Viewport>
            {options.map((option) => (
              <SelectPrimitive.Item
                key={option.value}
                value={option.value}
                className="relative flex cursor-pointer items-center gap-2 rounded-md py-1.5 pr-8 pl-2 text-[13px] text-fg outline-none select-none data-[highlighted]:bg-surface-active"
              >
                {option.leading}
                <div className="min-w-0">
                  <SelectPrimitive.ItemText>{option.label}</SelectPrimitive.ItemText>
                  {option.hint ? <div className="text-2xs text-fg-subtle">{option.hint}</div> : null}
                </div>
                <SelectPrimitive.ItemIndicator className="absolute right-2">
                  <Check className="size-3.5 text-brand" />
                </SelectPrimitive.ItemIndicator>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  )
}
