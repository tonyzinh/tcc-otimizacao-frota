import { FlaskConical, TriangleAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Tooltip } from '@/components/ui/tooltip'
import { cn } from '@/lib/cn'
import type { DataKind, Provenance } from '@/types'

const KIND_LABEL: Record<DataKind, string> = {
  demo: 'Dados fictícios',
  synthetic: 'Dados sintéticos',
  real: 'Dados reais autorizados',
}

/** Selo de proveniência. Sempre visível onde há números ou mapas. */
export function DataKindBadge({ provenance, className }: { provenance: Provenance | undefined; className?: string }) {
  const kind = provenance?.kind ?? 'demo'
  return (
    <Tooltip content={provenance?.disclaimer ?? 'Origem dos dados não informada.'}>
      <span tabIndex={0} className={cn('inline-flex rounded-[5px] outline-none', className)}>
        <Badge variant={kind === 'real' ? 'neutral' : 'demo'} size="sm" className="uppercase">
          <FlaskConical aria-hidden />
          {KIND_LABEL[kind]}
        </Badge>
      </span>
    </Tooltip>
  )
}

/** Faixa discreta reforçando que o painel é demonstrativo e não despacho em tempo real. */
export function DemoStrip({ className }: { className?: string }) {
  return (
    <div
      role="note"
      className={cn(
        'flex items-start gap-2 rounded-lg border border-warning/25 bg-warning/[0.06] px-3 py-2 text-xs text-fg-muted',
        className,
      )}
    >
      <TriangleAlert className="mt-px size-3.5 shrink-0 text-warning" aria-hidden />
      <p>
        <span className="font-medium text-fg">Demonstração com dados fictícios.</span> Planejamento D+1 calculado no corte de D,
        avaliado por replay retrospectivo — não é despacho em tempo real nem medição da empresa.
      </p>
    </div>
  )
}
