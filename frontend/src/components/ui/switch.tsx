import { Switch as SwitchPrimitive } from 'radix-ui'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/cn'

export function Switch({ className, ...props }: ComponentProps<typeof SwitchPrimitive.Root>) {
  return (
    <SwitchPrimitive.Root
      className={cn(
        'inline-flex h-4 w-7 shrink-0 cursor-pointer items-center rounded-full border border-line-strong bg-surface-active p-px transition-colors data-[state=checked]:border-transparent data-[state=checked]:bg-brand disabled:cursor-not-allowed disabled:opacity-40',
        className,
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb className="block size-3 rounded-full bg-fg-muted transition-transform duration-150 data-[state=checked]:translate-x-3 data-[state=checked]:bg-brand-ink" />
    </SwitchPrimitive.Root>
  )
}
