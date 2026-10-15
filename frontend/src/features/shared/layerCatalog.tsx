import { Car, Flame, Hexagon, Map as MapIcon, MapPin, Orbit, Route, Spline, Waypoints, Radar } from 'lucide-react'
import type { LayerToggleItem } from './LayerToggles'
import type { LayerKey } from './scenarioLayers'

/** Catálogo das camadas disponíveis (rótulo, dica e ícone) compartilhado entre as telas. */
export const LAYER_ITEMS: Record<LayerKey, LayerToggleItem<LayerKey>> = {
  basemap: { key: 'basemap', label: 'Base cartográfica', hint: 'OpenFreeMap · OSM', icon: <MapIcon /> },
  demand: { key: 'demand', label: 'Demanda prevista (H3)', hint: 'Conhecida no corte de D', icon: <Hexagon /> },
  heat: { key: 'heat', label: 'Calor de solicitações', hint: 'Observadas em D+1 até o instante', icon: <Flame /> },
  requests: { key: 'requests', label: 'Solicitações', hint: 'Aguardando, atendidas, não atendidas', icon: <MapPin /> },
  vehicles: { key: 'vehicles', label: 'Veículos', hint: 'Posição no instante', icon: <Car /> },
  planned: { key: 'planned', label: 'Reposicionamento planejado', hint: 'Tracejado', icon: <Spline /> },
  executed: { key: 'executed', label: 'Reposicionamento executado', hint: 'Linha contínua', icon: <Route /> },
  trails: { key: 'trails', label: 'Trilhas acumuladas', hint: 'Transparência progressiva', icon: <Waypoints /> },
  flows: { key: 'flows', label: 'Fluxos entre zonas', hint: 'Arcos agregados por par H3', icon: <Orbit /> },
  concentration: { key: 'concentration', label: 'Concentração da frota livre', hint: 'Descritivo visual', icon: <Radar /> },
}

export function layerItems(keys: readonly LayerKey[]): LayerToggleItem<LayerKey>[] {
  return keys.map((k) => LAYER_ITEMS[k])
}
