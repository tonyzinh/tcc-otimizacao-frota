import { CircleSlash, Flag, MapPin, Navigation, UserCheck, Waypoints } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'
import { formatClock, formatKm } from '@/lib/format'
import type { DaySnapshot, ScenarioRun, SimulationEvent, SimulationEventType } from '@/types'

const ICONS: Record<SimulationEventType, ReactNode> = {
  request_created: <MapPin />,
  dispatch: <Navigation />,
  pickup: <UserCheck />,
  dropoff: <Flag />,
  request_unserved: <CircleSlash />,
  reposition_start: <Waypoints />,
  reposition_end: <Waypoints />,
}

function describe(e: SimulationEvent, localityOf: (requestId: string | null, movementId: string | null) => string): string {
  switch (e.type) {
    case 'request_created':
      return `${e.requestId} criada em ${localityOf(e.requestId, null)}`
    case 'dispatch':
      return `${e.vehicleId} despachado para ${e.requestId} · ${formatKm(e.km, 1)} de pickup`
    case 'pickup':
      return `${e.vehicleId} embarcou ${e.requestId}`
    case 'dropoff':
      return `${e.vehicleId} concluiu ${e.requestId}`
    case 'request_unserved':
      return `${e.requestId} sem veículo livre no limite de pickup`
    case 'reposition_start':
      return `${e.vehicleId} iniciou reposicionamento · ${formatKm(e.km, 1)}`
    case 'reposition_end':
      return `${e.vehicleId} chegou a ${localityOf(null, e.movementId)}`
  }
}

/** Últimos eventos até o instante do replay (mais recentes primeiro). */
export function EventLog({
  run,
  snapshot,
  upToIndex,
  limit = 9,
}: {
  run: ScenarioRun
  snapshot: DaySnapshot
  upToIndex: number
  limit?: number
}) {
  const zones = new Map(snapshot.zones.map((z) => [z.h3, z.locality]))
  const requestZone = new Map(snapshot.requests.map((r) => [r.id, r.originZone]))
  const movementZone = new Map(run.movements.map((m) => [m.id, m.toZone]))
  const localityOf = (requestId: string | null, movementId: string | null) => {
    const zone = requestId ? requestZone.get(requestId) : movementId ? movementZone.get(movementId) : undefined
    return (zone && zones.get(zone)) ?? 'zona sem previsão'
  }
  const items = run.events.slice(Math.max(0, upToIndex - limit), upToIndex).reverse()
  if (items.length === 0) {
    return <p className="px-4 py-3 text-xs text-fg-subtle">Nenhum evento até este instante.</p>
  }
  return (
    <ol className="grid gap-0.5 px-2 pb-2" aria-live="off">
      {items.map((e, i) => (
        <li
          key={e.id}
          className={cn(
            'flex items-start gap-2 rounded-md px-2 py-1.5 text-xs transition-colors',
            i === 0 ? 'bg-surface-raised text-fg' : 'text-fg-muted',
          )}
        >
          <span
            className={cn(
              'mt-px flex size-4 shrink-0 items-center justify-center [&_svg]:size-3',
              e.type === 'request_unserved' ? 'text-critical-text' : 'text-fg-subtle',
            )}
          >
            {ICONS[e.type]}
          </span>
          <span className="w-10 shrink-0 font-mono text-[10.5px] text-fg-subtle tabular">{formatClock(Date.parse(e.t))}</span>
          <span className="min-w-0 flex-1">{describe(e, localityOf)}</span>
        </li>
      ))}
    </ol>
  )
}
