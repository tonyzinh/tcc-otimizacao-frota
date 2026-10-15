/**
 * Fábricas de camadas deck.gl. Cada função recebe dados já transformados e um estilo, e devolve
 * camadas prontas para o `FleetMap`. Nenhuma calcula indicador científico.
 */
import type { Layer } from '@deck.gl/core'
import { HeatmapLayer } from '@deck.gl/aggregation-layers'
import { PathStyleExtension, type PathStyleExtensionProps } from '@deck.gl/extensions'
import { H3HexagonLayer, TripsLayer } from '@deck.gl/geo-layers'
import { ArcLayer, PathLayer, ScatterplotLayer } from '@deck.gl/layers'
import type { Trail } from '@/components/simulation/replayEngine'
import { rampColor, type MapPalette, type RGB } from '@/theme/colors'
import type { DemandZone, LngLat, RepositionMovement, VehicleFrame, VehicleState } from '@/types'
import type { VisibleRequest, ZoneFlow } from './transforms'

type RGBA = [number, number, number, number]
const withAlpha = (c: RGB, a: number): RGBA => [c[0], c[1], c[2], a]

const dashExtension = new PathStyleExtension({ dash: true })

/** Converte caminhos imutáveis em posições aceitas pelo deck.gl. */
const toPositions = (path: readonly LngLat[]): [number, number][] => path.map((p) => [p[0], p[1]])

export function demandHexLayer(opts: {
  id?: string
  zones: readonly DemandZone[]
  palette: MapPalette
  metric: 'forecastRides' | 'observedRides'
  minValue?: number
  selectedZone?: string | null
  opacity?: number
}): Layer {
  const { zones, palette, metric, minValue = 0, selectedZone = null, opacity = 0.5 } = opts
  const data = zones.filter((z) => z[metric] >= minValue)
  const max = Math.max(1, ...zones.map((z) => z[metric]))
  return new H3HexagonLayer<DemandZone>({
    id: opts.id ?? 'demand-hex',
    data,
    getHexagon: (z) => z.h3,
    getFillColor: (z) => {
      const ratio = Math.sqrt(z[metric] / max)
      return withAlpha(rampColor(palette.demandRamp, ratio), Math.round(70 + 185 * ratio))
    },
    getLineColor: (z) => (z.h3 === selectedZone ? [255, 255, 255, 230] : [255, 255, 255, 18]),
    getLineWidth: (z) => (z.h3 === selectedZone ? 2 : 0.5),
    lineWidthUnits: 'pixels',
    extruded: false,
    stroked: true,
    filled: true,
    opacity,
    pickable: true,
    autoHighlight: true,
    highlightColor: [255, 255, 255, 40],
    updateTriggers: { getLineColor: selectedZone, getLineWidth: selectedZone, getFillColor: [metric, max] },
  })
}

export function requestHeatLayer(opts: { id?: string; points: readonly LngLat[]; palette: MapPalette }): Layer {
  return new HeatmapLayer<LngLat>({
    id: opts.id ?? 'request-heat',
    data: opts.points as LngLat[],
    getPosition: (p) => [p[0], p[1]],
    getWeight: 1,
    radiusPixels: 42,
    intensity: 1.1,
    threshold: 0.04,
    colorRange: opts.palette.heatRamp.map((c, i) => withAlpha(c, 60 + i * 45)),
    aggregation: 'SUM',
  })
}

export function requestsLayer(opts: {
  id?: string
  requests: readonly VisibleRequest[]
  palette: MapPalette
  selectedId?: string | null
}): Layer {
  const { palette, selectedId = null } = opts
  const color = (s: VisibleRequest['state']): RGB =>
    s === 'unserved' ? palette.requestUnserved : s === 'waiting' ? palette.requestWaiting : palette.requestServed
  return new ScatterplotLayer<VisibleRequest>({
    id: opts.id ?? 'requests',
    data: opts.requests as VisibleRequest[],
    getPosition: (r) => [r.request.origin[0], r.request.origin[1]],
    getRadius: (r) => (r.request.id === selectedId ? 7 : r.state === 'served' ? 2.6 : 4.2),
    radiusUnits: 'pixels',
    stroked: true,
    filled: true,
    getFillColor: (r) => withAlpha(color(r.state), r.state === 'served' ? 70 : 40),
    getLineColor: (r) => withAlpha(color(r.state), r.state === 'served' ? 110 : 255),
    getLineWidth: (r) => (r.state === 'served' ? 1 : 1.6),
    lineWidthUnits: 'pixels',
    pickable: true,
    updateTriggers: { getRadius: selectedId },
  })
}

export function vehiclesLayers(opts: {
  idPrefix?: string
  frames: readonly VehicleFrame[]
  palette: MapPalette
  strategyColor: RGB
  visibleStates: ReadonlySet<VehicleState>
  selectedId?: string | null
}): Layer[] {
  const { palette, strategyColor, visibleStates, selectedId = null } = opts
  const prefix = opts.idPrefix ?? 'vehicles'
  const data = opts.frames.filter((f) => visibleStates.has(f.state))
  const fill = (f: VehicleFrame): RGBA => {
    if (f.state === 'repositioning') return withAlpha(strategyColor, 255)
    if (f.state === 'unavailable') return withAlpha(palette.vehicle.unavailable, 150)
    return withAlpha(palette.vehicle[f.state], 255)
  }
  const halo = new ScatterplotLayer<VehicleFrame>({
    id: `${prefix}-halo`,
    data: data.filter((f) => f.state === 'repositioning' || f.vehicleId === selectedId),
    getPosition: (f) => [f.position[0], f.position[1]],
    getRadius: (f) => (f.vehicleId === selectedId ? 14 : 11),
    radiusUnits: 'pixels',
    getFillColor: (f) => (f.vehicleId === selectedId ? [255, 255, 255, 40] : withAlpha(strategyColor, 55)),
    updateTriggers: { getRadius: selectedId, getFillColor: [selectedId, strategyColor] },
  })
  const dots = new ScatterplotLayer<VehicleFrame>({
    id: `${prefix}-dots`,
    data,
    getPosition: (f) => [f.position[0], f.position[1]],
    getRadius: (f) => (f.state === 'unavailable' ? 3 : f.vehicleId === selectedId ? 6.5 : 4.6),
    radiusUnits: 'pixels',
    stroked: true,
    getFillColor: fill,
    getLineColor: withAlpha(palette.vehicleOutline, 230),
    getLineWidth: 1.4,
    lineWidthUnits: 'pixels',
    pickable: true,
    updateTriggers: { getFillColor: [strategyColor], getRadius: selectedId },
  })
  return [halo, dots]
}

export function plannedMovesLayer(opts: {
  id?: string
  movements: readonly RepositionMovement[]
  strategyColor: RGB
  palette: MapPalette
  selectedId?: string | null
}): Layer {
  const { strategyColor, palette, selectedId = null } = opts
  return new PathLayer<RepositionMovement, PathStyleExtensionProps<RepositionMovement>>({
    id: opts.id ?? 'moves-planned',
    data: opts.movements as RepositionMovement[],
    getPath: (m) => toPositions(m.plannedPath),
    getColor: (m) =>
      m.outcome === 'executed' ? withAlpha(strategyColor, m.id === selectedId ? 255 : 150) : withAlpha(palette.notExecuted, m.id === selectedId ? 255 : 150),
    getWidth: (m) => (m.id === selectedId ? 2.6 : 1.4),
    widthUnits: 'pixels',
    capRounded: true,
    jointRounded: true,
    getDashArray: [5, 4],
    dashUnits: 'pixels',
    dashJustified: true,
    extensions: [dashExtension],
    pickable: true,
    updateTriggers: { getColor: [selectedId, strategyColor], getWidth: selectedId },
  })
}

export function executedMovesLayer(opts: {
  id?: string
  movements: readonly RepositionMovement[]
  strategyColor: RGB
  selectedId?: string | null
}): Layer {
  const { strategyColor, selectedId = null } = opts
  const data = opts.movements.filter((m) => m.outcome === 'executed' && m.executedPath)
  return new PathLayer<RepositionMovement>({
    id: opts.id ?? 'moves-executed',
    data,
    getPath: (m) => toPositions(m.executedPath ?? []),
    getColor: (m) => withAlpha(strategyColor, m.id === selectedId ? 255 : 215),
    getWidth: (m) => (m.id === selectedId ? 3.4 : 2.2),
    widthUnits: 'pixels',
    capRounded: true,
    jointRounded: true,
    pickable: true,
    updateTriggers: { getColor: [selectedId, strategyColor], getWidth: selectedId },
  })
}

/** Endpoints dos movimentos executados (origem vazada, destino sólido). */
export function moveEndpointsLayer(opts: { id?: string; movements: readonly RepositionMovement[]; strategyColor: RGB }): Layer {
  const points = opts.movements
    .filter((m) => m.outcome === 'executed')
    .map((m) => ({ position: m.to, id: m.id }))
  return new ScatterplotLayer<{ position: LngLat; id: string }>({
    id: opts.id ?? 'moves-endpoints',
    data: points,
    getPosition: (p) => [p.position[0], p.position[1]],
    getRadius: 2.4,
    radiusUnits: 'pixels',
    getFillColor: withAlpha(opts.strategyColor, 255),
    updateTriggers: { getFillColor: opts.strategyColor },
  })
}

/**
 * Trilhas animadas estilo "colônia": a cabeça é intensa e o histórico acumulado esmaece com o
 * tempo (transparência progressiva). Só reflete deslocamentos existentes nos eventos.
 */
export function trailLayers(opts: {
  idPrefix?: string
  trails: readonly Trail[]
  currentSec: number
  strategyColor: RGB
  palette: MapPalette
  kinds: ReadonlySet<Trail['kind']>
  accumulate: boolean
  headSeconds?: number
}): Layer[] {
  const { currentSec, strategyColor, palette, kinds, accumulate, headSeconds = 420 } = opts
  const prefix = opts.idPrefix ?? 'trails'
  const data = opts.trails.filter((t) => kinds.has(t.kind))
  const colorOf = (t: Trail): RGB =>
    t.kind === 'repositioning' ? strategyColor : t.kind === 'to_pickup' ? palette.pickupTrail : palette.tripTrail
  const widthOf = (t: Trail) => (t.kind === 'repositioning' ? 3 : t.kind === 'to_pickup' ? 1.8 : 1.2)
  const layers: Layer[] = []
  if (accumulate) {
    layers.push(
      new TripsLayer<Trail>({
        id: `${prefix}-history`,
        data,
        getPath: (t) => toPositions(t.path),
        getTimestamps: (t) => t.timestamps,
        getColor: (t) => withAlpha(colorOf(t), t.kind === 'on_trip' ? 40 : 95),
        getWidth: widthOf,
        widthUnits: 'pixels',
        capRounded: true,
        jointRounded: true,
        fadeTrail: true,
        trailLength: 3 * 3600,
        currentTime: currentSec,
        updateTriggers: { getColor: [strategyColor] },
      }),
    )
  }
  layers.push(
    new TripsLayer<Trail>({
      id: `${prefix}-head`,
      data,
      getPath: (t) => toPositions(t.path),
      getTimestamps: (t) => t.timestamps,
      getColor: (t) => withAlpha(colorOf(t), t.kind === 'on_trip' ? 110 : 255),
      getWidth: (t) => widthOf(t) + 0.6,
      widthUnits: 'pixels',
      capRounded: true,
      jointRounded: true,
      fadeTrail: true,
      trailLength: headSeconds,
      currentTime: currentSec,
      updateTriggers: { getColor: [strategyColor] },
    }),
  )
  return layers
}

export function flowLayer(opts: { id?: string; flows: readonly ZoneFlow[]; strategyColor: RGB; selectedId?: string | null }): Layer {
  const max = Math.max(1, ...opts.flows.map((f) => f.count))
  return new ArcLayer<ZoneFlow>({
    id: opts.id ?? 'flows',
    data: opts.flows as ZoneFlow[],
    getSourcePosition: (f) => [f.from[0], f.from[1]],
    getTargetPosition: (f) => [f.to[0], f.to[1]],
    getSourceColor: withAlpha(opts.strategyColor, 40),
    getTargetColor: withAlpha(opts.strategyColor, 235),
    getWidth: (f) => 1 + (f.count / max) * 5,
    widthUnits: 'pixels',
    getHeight: 0.45,
    greatCircle: false,
    pickable: true,
    updateTriggers: { getSourceColor: opts.strategyColor, getTargetColor: opts.strategyColor },
  })
}

/** Concentração da frota livre (brilho neutro), descritivo visual. */
export function idleConcentrationLayer(opts: { id?: string; frames: readonly VehicleFrame[]; dark: boolean }): Layer {
  const base: RGB = opts.dark ? [236, 238, 241] : [40, 44, 52]
  return new HeatmapLayer<VehicleFrame>({
    id: opts.id ?? 'idle-concentration',
    data: opts.frames.filter((f) => f.state === 'idle'),
    getPosition: (f) => [f.position[0], f.position[1]],
    radiusPixels: 55,
    intensity: 1,
    threshold: 0.08,
    colorRange: [20, 45, 80, 120, 170, 220].map((a) => withAlpha(base, a)),
  })
}
