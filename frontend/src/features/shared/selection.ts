import type { PickingInfo } from '@deck.gl/core'
import type { ZoneFlow, VisibleRequest } from '@/components/maps/transforms'
import type { DemandZone, RepositionMovement, VehicleFrame } from '@/types'

/** Objeto selecionado no mapa, independente da camada que o desenhou. */
export type MapSelection =
  | { kind: 'zone'; id: string }
  | { kind: 'vehicle'; id: string }
  | { kind: 'movement'; id: string }
  | { kind: 'request'; id: string }
  | { kind: 'flow'; id: string }

export function selectionFromObject(layerId: string, object: unknown): MapSelection | null {
  if (!object) return null
  const prefix = layerId.replace(/^(a|b)-/, '')
  if (prefix.startsWith('demand-hex')) return { kind: 'zone', id: (object as DemandZone).h3 }
  if (prefix.startsWith('vehicles')) return { kind: 'vehicle', id: (object as VehicleFrame).vehicleId }
  if (prefix.startsWith('moves')) return { kind: 'movement', id: (object as RepositionMovement).id }
  if (prefix.startsWith('requests')) return { kind: 'request', id: (object as VisibleRequest).request.id }
  if (prefix.startsWith('flows')) return { kind: 'flow', id: (object as ZoneFlow).id }
  return null
}

export function selectionFromPick(info: PickingInfo): MapSelection | null {
  return selectionFromObject(info.layer?.id ?? '', info.object)
}
