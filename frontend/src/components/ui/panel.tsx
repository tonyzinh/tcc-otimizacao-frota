import type { ComponentProps, ReactNode } from 'react'
import { cn } from '@/lib/cn'

/** Superfície plana com borda fina. Substitui "cards" pesados. */
export function Panel({ className, ...props }: ComponentProps<'section'>) {
  return <section data-slot="panel" className={cn('rounded-xl border border-line bg-surface', className)} {...props} />
}

export function PanelHeader({
  title,
  description,
  actions,
  className,
  eyebrow,
}: {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  eyebrow?: ReactNode
  className?: string
}) {
  return (
    <header className={cn('flex flex-wrap items-start justify-between gap-x-4 gap-y-2 px-4 pt-3.5 pb-3', className)}>
      <div className="min-w-0">
        {eyebrow ? <div className="eyebrow mb-1">{eyebrow}</div> : null}
        <h2 className="text-[13px] font-semibold tracking-tight text-fg">{title}</h2>
        {description ? <p className="mt-0.5 text-xs text-fg-subtle">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-1.5">{actions}</div> : null}
    </header>
  )
}

export function PanelBody({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('px-4 pb-4', className)} {...props} />
}

/** Painel flutuante translúcido sobre o mapa. */
export function FloatingPanel({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      data-slot="floating-panel"
      className={cn('glass rounded-xl border border-line shadow-panel', className)}
      {...props}
    />
  )
}
