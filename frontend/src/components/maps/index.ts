import { lazy } from 'react'

/** Carregado sob demanda: MapLibre e deck.gl ficam fora do pacote inicial. */
export const FleetMap = lazy(() => import('./FleetMap'))
export type { FleetMapProps, MapHover } from './FleetMap'
export { createMapSync, type MapSync } from './mapSync'
export { MapLegend, type LegendItem } from './MapLegend'
