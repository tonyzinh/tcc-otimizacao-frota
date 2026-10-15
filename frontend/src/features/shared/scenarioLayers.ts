import type { Layer } from '@deck.gl/core'
import { useMemo } from 'react'
import {
  demandHexLayer,
  executedMovesLayer,
  flowLayer,
  idleConcentrationLayer,
  moveEndpointsLayer,
  plannedMovesLayer,
  requestHeatLayer,
  requestsLayer,
  trailLayers,
  vehiclesLayers,
} from '@/components/maps/layers'
import type { LegendItem } from '@/components/maps/MapLegend'
import { aggregateFlows, visibleRequests, type VisibleRequest, type ZoneFlow } from '@/components/maps/transforms'
import type { ReplayFrame } from '@/types'
import type { RequestDisplayState, ReplayModel, Trail } from '@/components/simulation/replayEngine'
import { MAP_PALETTE, seriesRgb } from '@/theme/colors'
import type { Theme } from '@/theme/ThemeProvider'
import type { AlgorithmId, DaySnapshot, LngLat, RepositionMovement, ScenarioRun, VehicleState } from '@/types'
import type { MapSelection } from './selection'

export type LayerKey =
  | 'basemap'
  | 'demand'
  | 'heat'
  | 'requests'
  | 'vehicles'
  | 'planned'
  | 'executed'
  | 'trails'
  | 'flows'
  | 'concentration'

export type ExecutionFilter = 'all' | 'executed' | 'not_executed'

export interface ScenarioLayerInput {
  idPrefix: string
  theme: Theme
  snapshot: DaySnapshot
  run: ScenarioRun
  model: ReplayModel
  frame: ReplayFrame
  layers: Record<LayerKey, boolean>
  vehicleStates: ReadonlySet<VehicleState>
  requestStates: ReadonlySet<RequestDisplayState>
  executionFilter: ExecutionFilter
  minDemand: number
  selection: MapSelection | null
  trails: { accumulate: boolean; headSeconds: number; kinds: ReadonlySet<Trail['kind']> }
}

interface DerivedLayerData {
  movements: RepositionMovement[]
  flows: ZoneFlow[]
  requests: VisibleRequest[]
  heatPoints: LngLat[]
}

function filterMovements(movements: readonly RepositionMovement[], filter: ExecutionFilter): RepositionMovement[] {
  if (filter === 'all') return [...movements]
  return movements.filter((m) => (filter === 'executed' ? m.outcome === 'executed' : m.outcome !== 'executed'))
}

/** Monta a pilha de camadas (de baixo para cima) a partir dos dados já derivados. */
export function buildScenarioLayers(input: ScenarioLayerInput, derived: DerivedLayerData): Layer[] {
  const { idPrefix, theme, snapshot, run, model, frame, layers, vehicleStates, minDemand, selection, trails } = input
  const { movements, flows, requests, heatPoints } = derived
  const palette = MAP_PALETTE[theme]
  const strategyColor = seriesRgb(theme, run.algorithmId)
  const selectedOf = (kind: MapSelection['kind']) => (selection?.kind === kind ? selection.id : null)
  const id = (name: string) => `${idPrefix}${name}`
  const out: Layer[] = []
  if (layers.demand) {
    out.push(
      demandHexLayer({ id: id('demand-hex'), zones: snapshot.zones, palette, metric: 'forecastRides', minValue: minDemand, selectedZone: selectedOf('zone') }),
    )
  }
  if (layers.heat && heatPoints.length > 0) out.push(requestHeatLayer({ id: id('request-heat'), points: heatPoints, palette }))
  if (layers.concentration) out.push(idleConcentrationLayer({ id: id('idle-concentration'), frames: frame.vehicles, dark: theme === 'dark' }))
  if (layers.flows && flows.length > 0) out.push(flowLayer({ id: id('flows'), flows, strategyColor, selectedId: selectedOf('flow') }))
  if (layers.planned && movements.length > 0) {
    out.push(plannedMovesLayer({ id: id('moves-planned'), movements, strategyColor, palette, selectedId: selectedOf('movement') }))
  }
  if (layers.executed && movements.length > 0) {
    out.push(executedMovesLayer({ id: id('moves-executed'), movements, strategyColor, selectedId: selectedOf('movement') }))
    out.push(moveEndpointsLayer({ id: id('moves-endpoints'), movements, strategyColor }))
  }
  if (layers.trails) {
    out.push(
      ...trailLayers({
        idPrefix: id('trails'),
        trails: model.trails,
        currentSec: (frame.t - model.windowStart) / 1000,
        strategyColor,
        palette,
        kinds: trails.kinds,
        accumulate: trails.accumulate,
        headSeconds: trails.headSeconds,
      }),
    )
  }
  if (layers.requests) out.push(requestsLayer({ id: id('requests'), requests, palette, selectedId: selectedOf('request') }))
  if (layers.vehicles) {
    out.push(
      ...vehiclesLayers({
        idPrefix: id('vehicles'),
        frames: frame.vehicles,
        palette,
        strategyColor,
        visibleStates: vehicleStates,
        selectedId: selectedOf('vehicle'),
      }),
    )
  }
  return out
}

/**
 * Camadas de um cenário. Aceita `null` enquanto os dados carregam (os hooks continuam sendo
 * chamados na mesma ordem). Derivações caras são memorizadas; o tempo é arredondado a 15 s.
 */
export function useScenarioLayers(input: ScenarioLayerInput | null): Layer[] {
  const run = input?.run
  const snapshot = input?.snapshot
  const model = input?.model
  const executionFilter = input?.executionFilter ?? 'all'
  const requestStates = input?.requestStates
  const tBucket = Math.floor((input?.frame.t ?? 0) / 15_000) * 15_000

  const movements = useMemo(() => (run ? filterMovements(run.movements, executionFilter) : []), [run, executionFilter])
  const flows = useMemo(() => (snapshot ? aggregateFlows(movements, snapshot.zones, 'planned') : []), [movements, snapshot])
  const requests = useMemo(
    () => (model && requestStates ? visibleRequests(model.requests, tBucket, requestStates) : []),
    [model, tBucket, requestStates],
  )
  const heatPoints = useMemo(
    () => (model ? model.requests.filter((r) => r.createdAt <= tBucket).map((r) => r.origin) : []),
    [model, tBucket],
  )
  if (!input) return []
  return buildScenarioLayers(input, { movements, flows, requests, heatPoints })
}

export function buildLegend(
  theme: Theme,
  algorithmId: AlgorithmId,
  algorithmName: string,
  layers: Record<LayerKey, boolean>,
): LegendItem[] {
  const p = MAP_PALETTE[theme]
  const s = seriesRgb(theme, algorithmId)
  const items: LegendItem[] = []
  if (layers.demand) items.push({ id: 'demand', label: 'Demanda prevista (H3)', swatch: { kind: 'ramp', colors: p.demandRamp } })
  if (layers.heat) items.push({ id: 'heat', label: 'Calor de solicitações', swatch: { kind: 'ramp', colors: p.heatRamp } })
  if (layers.planned) {
    items.push({ id: 'planned', label: `Planejado · ${algorithmName}`, swatch: { kind: 'dash', color: s } })
    items.push({ id: 'not-exec', label: 'Planejado, não executado', swatch: { kind: 'dash', color: p.notExecuted } })
  }
  if (layers.executed) items.push({ id: 'executed', label: 'Reposicionamento executado', swatch: { kind: 'line', color: s } })
  if (layers.trails) {
    items.push({ id: 'trail-r', label: 'Rastro de reposicionamento', swatch: { kind: 'fade', color: s } })
    items.push({ id: 'trail-p', label: 'Rastro de pickup (vazio)', swatch: { kind: 'fade', color: p.pickupTrail } })
  }
  if (layers.flows) items.push({ id: 'flows', label: 'Fluxo entre zonas', swatch: { kind: 'fade', color: s } })
  if (layers.vehicles) {
    items.push({ id: 'v-idle', label: 'Veículo livre', swatch: { kind: 'dot', color: p.vehicle.idle } })
    items.push({ id: 'v-repo', label: 'Reposicionando', swatch: { kind: 'dot', color: s, ring: true } })
    items.push({ id: 'v-pick', label: 'A caminho do passageiro', swatch: { kind: 'dot', color: p.vehicle.to_pickup } })
    items.push({ id: 'v-trip', label: 'Em corrida', swatch: { kind: 'dot', color: p.vehicle.on_trip } })
  }
  if (layers.requests) {
    items.push({ id: 'r-wait', label: 'Solicitação aguardando', swatch: { kind: 'ring', color: p.requestWaiting } })
    items.push({ id: 'r-unserved', label: 'Solicitação não atendida', swatch: { kind: 'ring', color: p.requestUnserved } })
  }
  return items
}
