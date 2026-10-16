import { FlaskConical, TriangleAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Tooltip } from '@/components/ui/tooltip'
import { cn } from '@/lib/cn'
import type { DataKind, Provenance } from '@/types'
import { useStudyKind } from './ExperimentContext'

const KIND_LABEL: Record<DataKind, string> = {
  demo: 'Dados fictícios',
  synthetic: 'Dados sintéticos',
  real: 'Dados reais autorizados',
}

/** Selo de proveniência. Sempre visível onde há números ou mapas. */
export function DataKindBadge({ provenance, className }: { provenance: Provenance | undefined; className?: string }) {
  const study = useStudyKind()
  const kind = provenance?.kind ?? study.kind
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
  const { real, distance } = useStudyKind()
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
        {real ? (
          <>
            <span className="font-medium text-fg">Dados reais pseudonimizados, uso local.</span> Plano D+1 avaliado por simulação
            retrospectiva com baseline calibrado; KM estimado ({distance}). Não é despacho em tempo real, economia observada nem
            política da empresa.
          </>
        ) : (
          <>
            <span className="font-medium text-fg">Demonstração com dados fictícios.</span> Planejamento D+1 calculado no corte de D,
            avaliado por replay retrospectivo — não é despacho em tempo real nem medição da empresa.
          </>
        )}
      </p>
    </div>
  )
}

/** Aviso global quando a origem dos dados não responde (ex.: API local de dados reais desligada). */
export function DataErrorBanner() {
  const { real, error } = useStudyKind()
  if (!error) return null
  return (
    <div role="alert" className="flex items-start gap-2 border-b border-critical/30 bg-critical/[0.08] px-4 py-2 text-xs text-fg-muted">
      <TriangleAlert className="mt-px size-3.5 shrink-0 text-critical" aria-hidden />
      <p>
        <span className="font-medium text-fg">Não foi possível carregar os dados.</span> {error.message}.{' '}
        {real
          ? 'No modo de dados reais, deixe rodando na raiz do repositório: tcc-frota fleetlab-serve (com TCC_REAL_DATA_AUTHORIZED=YES) e recarregue a página.'
          : 'Recarregue a página.'}
      </p>
    </div>
  )
}
