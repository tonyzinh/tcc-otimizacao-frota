import { CircleAlert, Inbox } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn('animate-pulse-soft rounded-md bg-surface-active', className)} />
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  className,
}: {
  title: string
  description?: ReactNode
  icon?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-2 px-6 py-10 text-center', className)}>
      <div className="flex size-9 items-center justify-center rounded-full border border-line bg-surface-raised text-fg-subtle [&_svg]:size-4">
        {icon ?? <Inbox />}
      </div>
      <p className="text-[13px] font-medium text-fg">{title}</p>
      {description ? <p className="max-w-sm text-xs text-fg-subtle">{description}</p> : null}
      {action}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <EmptyState
      icon={<CircleAlert className="text-critical-text" />}
      title="Não foi possível carregar os dados"
      description={error.message}
      action={
        onRetry ? (
          <button type="button" onClick={onRetry} className="mt-1 text-xs text-fg-muted underline underline-offset-2 hover:text-fg">
            Tentar novamente
          </button>
        ) : null
      }
    />
  )
}

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="inline-flex h-[18px] min-w-[18px] items-center justify-center rounded border border-line-strong bg-surface-raised px-1 font-mono text-[10px] text-fg-muted">
      {children}
    </kbd>
  )
}
