import { cva, type VariantProps } from 'class-variance-authority'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/cn'

export const badgeVariants = cva(
  'inline-flex items-center gap-1 whitespace-nowrap rounded-[5px] border font-medium leading-none [&_svg]:size-3 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        neutral: 'border-line bg-surface-raised text-fg-muted',
        outline: 'border-line-strong text-fg-muted',
        brand: 'border-transparent bg-brand-soft text-brand',
        demo: 'border-warning/30 bg-warning/10 text-warning',
        good: 'border-good/30 bg-good/10 text-success-text',
        critical: 'border-critical/30 bg-critical/10 text-critical-text',
      },
      size: {
        sm: 'h-[18px] px-1.5 text-[10px] tracking-wide',
        md: 'h-5 px-1.5 text-2xs',
      },
    },
    defaultVariants: { variant: 'neutral', size: 'md' },
  },
)

export interface BadgeProps extends ComponentProps<'span'>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, size, ...props }: BadgeProps) {
  return <span data-slot="badge" className={cn(badgeVariants({ variant, size }), className)} {...props} />
}
