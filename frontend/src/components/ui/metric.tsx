import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export type DeltaTone = 'good' | 'bad' | 'neutral'

/**
 * Variação com ícone + texto (nunca só cor). `direction` descreve o sentido do número;
 * `tone` diz se isso é bom ou ruim para o indicador (KM menor é bom, cobertura maior é boa).
 */
export function Delta({
  value,
  tone,
  direction,
  className,
}: {
  value: string
  tone: DeltaTone
  direction: 'up' | 'down' | 'flat'
  className?: string
}) {
  const Icon = direction === 'down' ? ArrowDownRight : direction === 'up' ? ArrowUpRight : Minus
  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 text-xs font-medium tabular',
        tone === 'good' && 'text-success-text',
        tone === 'bad' && 'text-critical-text',
        tone === 'neutral' && 'text-fg-subtle',
        className,
      )}
    >
      <Icon className="size-3.5" aria-hidden />
      {value}
    </span>
  )
}

/** Indicador compacto: rótulo, valor e contexto. Usado em faixas de KPIs, não em cartões isolados. */
export function Metric({
  label,
  value,
  unit,
  context,
  delta,
  accent,
  className,
}: {
  label: ReactNode
  value: ReactNode
  unit?: ReactNode
  context?: ReactNode
  delta?: ReactNode
  accent?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex min-w-0 flex-col gap-1.5', className)}>
      <div className="flex items-center gap-1.5">
        {accent}
        <span className="eyebrow truncate">{label}</span>
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="text-[22px] leading-none font-semibold tracking-tight text-fg tabular">{value}</span>
        {unit ? <span className="text-xs text-fg-subtle">{unit}</span> : null}
      </div>
      {delta || context ? (
        <div className="flex min-h-4 flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-fg-subtle">
          {delta}
          {context ? <span className="truncate">{context}</span> : null}
        </div>
      ) : null}
    </div>
  )
}
