import { Slider as SliderPrimitive } from 'radix-ui'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/cn'

export function Slider({ className, thumbLabel, ...props }: ComponentProps<typeof SliderPrimitive.Root> & { thumbLabel: string }) {
  const count = (props.value ?? props.defaultValue ?? [0]).length
  return (
    <SliderPrimitive.Root
      className={cn('relative flex h-5 w-full touch-none items-center select-none data-[disabled]:opacity-40', className)}
      {...props}
    >
      <SliderPrimitive.Track className="relative h-1 w-full grow overflow-hidden rounded-full bg-surface-active">
        <SliderPrimitive.Range className="absolute h-full bg-fg-muted" />
      </SliderPrimitive.Track>
      {Array.from({ length: count }, (_, i) => (
        <SliderPrimitive.Thumb
          key={i}
          aria-label={thumbLabel}
          className="block size-3.5 cursor-grab rounded-full border-2 border-canvas bg-fg shadow-[0_0_0_1px_var(--border-strong)] transition-transform hover:scale-110 active:cursor-grabbing"
        />
      ))}
    </SliderPrimitive.Root>
  )
}
