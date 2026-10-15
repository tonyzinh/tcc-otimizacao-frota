import type { MapHover } from '@/components/maps'
import type { VisibleRequest, ZoneFlow } from '@/components/maps/transforms'
import { formatClock, formatKm, formatNumber } from '@/lib/format'
import type { DemandZone, RepositionMovement, VehicleFrame } from '@/types'
import { OUTCOME_LABELS, REQUEST_STATE_LABELS, VEHICLE_STATE_LABELS } from './labels'
import { selectionFromObject } from './selection'

/** Conteúdo curto do tooltip de hover, por tipo de objeto. */
export function MapTooltipContent({ hover }: { hover: MapHover }) {
  const sel = selectionFromObject(hover.layerId, hover.object)
  if (!sel) return null
  switch (sel.kind) {
    case 'zone': {
      const z = hover.object as DemandZone
      return (
        <div className="grid gap-0.5">
          <b className="font-medium">{z.locality}</b>
          <span className="text-fg-muted">Prevista: {formatNumber(z.forecastRides, 1)} · observada: {formatNumber(z.observedRides)}</span>
        </div>
      )
    }
    case 'vehicle': {
      const v = hover.object as VehicleFrame
      return (
        <div className="grid gap-0.5">
          <b className="font-mono font-medium">{v.vehicleId}</b>
          <span className="text-fg-muted">{VEHICLE_STATE_LABELS[v.state]}</span>
        </div>
      )
    }
    case 'movement': {
      const m = hover.object as RepositionMovement
      return (
        <div className="grid gap-0.5">
          <b className="font-medium">
            {m.id} · {m.vehicleId}
          </b>
          <span className="text-fg-muted">
            {OUTCOME_LABELS[m.outcome]} · {formatKm(m.executedKm ?? m.plannedKm)}
          </span>
        </div>
      )
    }
    case 'request': {
      const r = hover.object as VisibleRequest
      return (
        <div className="grid gap-0.5">
          <b className="font-mono font-medium">{r.request.id}</b>
          <span className="text-fg-muted">
            {REQUEST_STATE_LABELS[r.state]} · criada {formatClock(r.request.createdAt)}
          </span>
        </div>
      )
    }
    case 'flow': {
      const f = hover.object as ZoneFlow
      return (
        <div className="grid gap-0.5">
          <b className="font-medium">{formatNumber(f.count)} recomendações</b>
          <span className="text-fg-muted">{formatKm(f.km)} planejados no par de zonas</span>
        </div>
      )
    }
  }
}
