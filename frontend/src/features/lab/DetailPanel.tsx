import { useStudyKind } from '@/features/shared/ExperimentContext'
import { ArrowRight, Car, Hexagon, MapPin, Route, Waypoints, X } from 'lucide-react'
import type { ReactNode } from 'react'
import { aggregateFlows } from '@/components/maps/transforms'
import { requestStateAt, vehicleFrameAt, type ReplayModel } from '@/components/simulation/replayEngine'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { AlgorithmTag } from '@/features/shared/AlgorithmTag'
import { OUTCOME_LABELS, REQUEST_STATE_LABELS, VEHICLE_STATE_LABELS } from '@/features/shared/labels'
import type { MapSelection } from '@/features/shared/selection'
import { cn } from '@/lib/cn'
import { formatClock, formatKm, formatMinutes, formatNumber, formatPercent, formatSignedPercent } from '@/lib/format'
import { compareScenario } from '@/lib/metrics'
import { toEpoch } from '@/lib/time'
import type { Algorithm, DaySnapshot, ScenarioMetrics, ScenarioRun } from '@/types'

function Row({ label, value, muted }: { label: ReactNode; value: ReactNode; muted?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1">
      <dt className="text-xs text-fg-subtle">{label}</dt>
      <dd className={cn('text-right text-xs tabular', muted ? 'text-fg-muted' : 'text-fg')}>{value}</dd>
    </div>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-t border-line px-4 py-3 first:border-t-0">
      <h3 className="eyebrow mb-1.5">{title}</h3>
      <dl>{children}</dl>
    </section>
  )
}

function Heading({ icon, title, subtitle, onClose }: { icon: ReactNode; title: ReactNode; subtitle?: ReactNode; onClose?: () => void }) {
  return (
    <div className="flex items-start gap-2.5 px-4 pt-3.5 pb-3">
      <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md border border-line bg-surface-raised text-fg-muted [&_svg]:size-3.5">
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[13px] font-semibold text-fg">{title}</div>
        {subtitle ? <div className="truncate text-xs text-fg-subtle">{subtitle}</div> : null}
      </div>
      {onClose ? (
        <Button variant="ghost" size="icon-sm" aria-label="Fechar detalhes" onClick={onClose}>
          <X />
        </Button>
      ) : null}
    </div>
  )
}

export interface DetailContext {
  snapshot: DaySnapshot
  run: ScenarioRun
  baseline: ScenarioMetrics | undefined
  model: ReplayModel
  time: number
  algorithm: Algorithm | undefined
  algorithmName: string
}

export function DetailPanel({
  selection,
  onClose,
  ctx,
}: {
  selection: MapSelection | null
  onClose: () => void
  ctx: DetailContext
}) {
  const { snapshot, run, model, time } = ctx
  const { real, distance } = useStudyKind()
  const zoneName = (h3: string) => {
    const z = snapshot.zones.find((x) => x.h3 === h3)
    return z ? `${z.locality} · ${z.municipality}` : 'Zona sem previsão'
  }

  if (!selection) {
    const m = run.metrics
    const cmp = ctx.baseline && run.algorithmId !== 'baseline' ? compareScenario(ctx.baseline, m) : null
    return (
      <div>
        <Heading icon={<Route />} title={<AlgorithmTag id={run.algorithmId} name={ctx.algorithmName} />} subtitle="Resumo do cenário no dia" />
        {ctx.algorithm ? <p className="px-4 pb-3 text-xs text-fg-subtle">{ctx.algorithm.description}</p> : null}
        <Section title="Atendimento (controle)">
          <Row label="Solicitações" value={formatNumber(m.requests)} />
          <Row label="Atendidas" value={`${formatNumber(m.served)} · ${formatPercent(m.coverage)}`} />
          <Row label="Espera média estimada" value={formatMinutes(m.meanWaitMinutes)} />
        </Section>
        <Section title={`KM vazio estimado (${distance})`}>
          <Row label="Pickup" value={formatKm(m.pickupKm)} />
          <Row label="Reposicionamento" value={formatKm(m.repositionKm)} />
          <Row label="Retorno" value="não medido" muted />
          <Row label={<span className="font-medium text-fg">Total</span>} value={<b className="font-semibold">{formatKm(m.emptyKmTotal)}</b>} />
          {cmp ? (
            <Row
              label="Redução vs baseline"
              value={
                <span className={cn((cmp.reductionPercent ?? 0) > 0 ? 'text-success-text' : 'text-critical-text')}>
                  {formatSignedPercent(cmp.reductionPercent)}
                </span>
              }
            />
          ) : null}
        </Section>
        {run.algorithmId !== 'baseline' ? (
          <Section title="Plano preventivo">
            <Row label="Recomendações (corte)" value={formatNumber(m.plannedMoves)} />
            <Row label="Executadas no replay" value={formatNumber(m.executedMoves)} />
            <Row label="KM planejado" value={formatKm(m.plannedRepositionKm)} muted />
          </Section>
        ) : null}
        <p className="border-t border-line px-4 py-3 text-[11px] text-fg-subtle">
          Clique em zonas, veículos, solicitações ou trajetos para ver detalhes. Trajetos são curvas ilustrativas; os km vêm dos
          eventos ({distance}).
        </p>
      </div>
    )
  }

  if (selection.kind === 'zone') {
    const z = snapshot.zones.find((x) => x.h3 === selection.id)
    if (!z) return null
    const requests = model.requests.filter((r) => snapshot.requests.find((q) => q.id === r.id)?.originZone === z.h3)
    const served = requests.filter((r) => r.outcome === 'served').length
    const inbound = run.movements.filter((m) => m.toZone === z.h3)
    const outbound = run.movements.filter((m) => m.fromZone === z.h3)
    return (
      <div>
        <Heading icon={<Hexagon />} title={z.locality} subtitle={`${z.municipality} · H3 r7`} onClose={onClose} />
        <Section title="Demanda">
          <Row label="Prevista no corte" value={`${formatNumber(z.forecastRides, 1)} corridas`} />
          <Row label="Observada em D+1" value={`${formatNumber(z.observedRides)} corridas`} />
          <Row label="Atendidas neste cenário" value={requests.length ? `${served}/${requests.length}` : '—'} />
        </Section>
        <Section title="Reposicionamento">
          <Row label="Entradas planejadas" value={formatNumber(inbound.length)} />
          <Row label="Saídas planejadas" value={formatNumber(outbound.length)} />
          <Row label="Entradas executadas" value={formatNumber(inbound.filter((m) => m.outcome === 'executed').length)} />
        </Section>
        <p className="px-4 pb-3 font-mono text-[10.5px] break-all text-fg-subtle">{z.h3}</p>
      </div>
    )
  }

  if (selection.kind === 'vehicle') {
    const segments = model.tracks.get(selection.id)
    const frame = segments ? vehicleFrameAt(segments, time) : null
    const fleet = snapshot.fleetAtStart.find((f) => f.vehicleId === selection.id)
    const rides = model.requests.filter((r) => r.vehicleId === selection.id)
    const moves = run.movements.filter((m) => m.vehicleId === selection.id)
    return (
      <div>
        <Heading icon={<Car />} title={selection.id} subtitle={real ? 'Rótulo pseudônimo' : 'Identificador fictício'} onClose={onClose} />
        <Section title={`Às ${formatClock(time)}`}>
          <Row label="Estado" value={frame ? VEHICLE_STATE_LABELS[frame.state] : '—'} />
          <Row label="Disponível" value={fleet ? `${formatClock(toEpoch(fleet.availableFrom))}–${formatClock(toEpoch(fleet.availableUntil))}` : 'ausente no dia'} />
        </Section>
        <Section title="Atendimentos no cenário">
          <Row label="Corridas" value={formatNumber(rides.length)} />
          <Row label="Pickup acumulado" value={formatKm(rides.reduce((s, r) => s + (r.pickupKm ?? 0), 0))} />
        </Section>
        <Section title="Recomendações">
          {moves.length === 0 ? (
            <p className="text-xs text-fg-subtle">Nenhuma recomendação para este veículo.</p>
          ) : (
            moves.map((m) => (
              <Row
                key={m.id}
                label={<span className="font-mono text-[11px]">{m.id}</span>}
                value={`${OUTCOME_LABELS[m.outcome]} · ${formatKm(m.executedKm ?? m.plannedKm)}`}
              />
            ))
          )}
        </Section>
      </div>
    )
  }

  if (selection.kind === 'movement') {
    const m = run.movements.find((x) => x.id === selection.id)
    if (!m) return null
    return (
      <div>
        <Heading icon={<Waypoints />} title={`Recomendação ${m.id}`} subtitle={`Veículo ${m.vehicleId}`} onClose={onClose} />
        <div className="px-4 pb-3">
          <Badge variant={m.outcome === 'executed' ? 'good' : 'neutral'}>{OUTCOME_LABELS[m.outcome]}</Badge>
        </div>
        <Section title="Trajeto">
          <Row label="De" value={zoneName(m.fromZone)} />
          <Row label="Para" value={zoneName(m.toZone)} />
          <Row label="KM planejado (corte)" value={formatKm(m.plannedKm, 2)} />
          <Row label="KM executado (posição real)" value={formatKm(m.executedKm, 2)} />
        </Section>
        <Section title="Tempo">
          <Row label="Planejado em" value={`D−1 às ${formatClock(toEpoch(m.plannedAt))}`} />
          <Row label="Início previsto" value={formatClock(toEpoch(m.scheduledStart))} />
          <Row label="Execução" value={m.executedStart && m.executedEnd ? `${formatClock(toEpoch(m.executedStart))}–${formatClock(toEpoch(m.executedEnd))}` : '—'} />
        </Section>
      </div>
    )
  }

  if (selection.kind === 'request') {
    const r = model.requests.find((x) => x.id === selection.id)
    const raw = snapshot.requests.find((x) => x.id === selection.id)
    if (!r || !raw) return null
    const state = requestStateAt(r, time)
    return (
      <div>
        <Heading icon={<MapPin />} title={r.id} subtitle={zoneName(raw.originZone)} onClose={onClose} />
        <Section title="Solicitação">
          <Row label="Criada às" value={formatClock(r.createdAt)} />
          <Row label={`Estado às ${formatClock(time)}`} value={state ? REQUEST_STATE_LABELS[state] : 'ainda não criada'} />
          <Row label="Desfecho no cenário" value={r.outcome === 'served' ? 'Atendida' : 'Não atendida'} />
        </Section>
        {r.outcome === 'served' ? (
          <Section title="Atendimento">
            <Row label="Veículo" value={r.vehicleId ?? '—'} />
            <Row label="Pickup estimado" value={formatKm(r.pickupKm, 2)} />
            <Row label="Espera estimada" value={r.pickupAt ? formatMinutes((r.pickupAt - r.createdAt) / 60_000) : '—'} />
          </Section>
        ) : (
          <p className="px-4 pb-3 text-xs text-fg-subtle">Nenhum veículo livre dentro do limite de pickup no instante da solicitação.</p>
        )}
      </div>
    )
  }

  const flow = aggregateFlows(run.movements, snapshot.zones, 'planned').find((f) => f.id === selection.id)
  if (!flow) return null
  return (
    <div>
      <Heading icon={<ArrowRight />} title="Fluxo entre zonas" subtitle="Recomendações agregadas por par de zonas" onClose={onClose} />
      <Section title="Par de zonas">
        <Row label="Origem" value={zoneName(flow.fromZone)} />
        <Row label="Destino" value={zoneName(flow.toZone)} />
        <Row label="Recomendações" value={formatNumber(flow.count)} />
        <Row label="KM planejado" value={formatKm(flow.km)} />
      </Section>
    </div>
  )
}
