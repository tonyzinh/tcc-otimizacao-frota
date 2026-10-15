import type { LayersList, PickingInfo } from '@deck.gl/core'
import { MapboxOverlay } from '@deck.gl/mapbox'
import { MapPinOff } from 'lucide-react'
import {
  AttributionControl,
  Map as MapLibreMap,
  NavigationControl,
  setWorkerUrl,
  type LngLatBoundsLike,
  type PaddingOptions,
} from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { EmptyState } from '@/components/ui/feedback'
import { cn } from '@/lib/cn'
import { useTheme } from '@/theme/ThemeProvider'
import { BASEMAP_COLORS, buildBasemapStyle } from './basemapStyle'
import type { MapSync } from './mapSync'

// O MapLibre 6 resolve o worker relativo ao próprio módulo; com o pré-empacotamento do Vite
// essa URL quebra. Apontamos explicitamente para o arquivo servido/emitido pelo Vite.
setWorkerUrl(maplibreWorkerUrl)

/** Área com dados demonstrativos (Serra ao norte, Viana a oeste, Vila Velha ao sul). */
const DEFAULT_BOUNDS: LngLatBoundsLike = [
  [-40.5, -20.43],
  [-40.18, -20.11],
]

export interface MapHover {
  x: number
  y: number
  /** Largura do mapa, para manter o tooltip dentro da área visível. */
  width: number
  object: unknown
  layerId: string
}

export interface FleetMapProps {
  layers: LayersList
  ariaLabel: string
  basemap?: boolean
  /** Enquadramento inicial; o padrão cobre a área demonstrativa da Grande Vitória. */
  bounds?: LngLatBoundsLike
  /** Folga para painéis flutuantes sobre o mapa. */
  padding?: number | PaddingOptions
  sync?: MapSync
  onPick?: (info: PickingInfo) => void
  renderTooltip?: (hover: MapHover) => ReactNode
  className?: string
  children?: ReactNode
  showNavigation?: boolean
}

/**
 * Mapa base (MapLibre GL) com camadas deck.gl sobrepostas. Componente de renderização apenas:
 * recebe camadas prontas e devolve interações (clique/hover) ao chamador.
 */
export default function FleetMap({
  layers,
  ariaLabel,
  basemap = true,
  bounds = DEFAULT_BOUNDS,
  padding = 24,
  sync,
  onPick,
  renderTooltip,
  className,
  children,
  showNavigation = true,
}: FleetMapProps) {
  const { theme } = useTheme()
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const overlayRef = useRef<MapboxOverlay | null>(null)
  const pickRef = useRef(onPick)
  const tooltipEnabledRef = useRef(Boolean(renderTooltip))
  const initialStyle = useRef({ theme, basemap })
  const initialView = useRef({ bounds, padding })
  const [hover, setHover] = useState<MapHover | null>(null)
  const [failed, setFailed] = useState<string | null>(null)
  const [map, setMap] = useState<MapLibreMap | null>(null)

  useEffect(() => {
    pickRef.current = onPick
    tooltipEnabledRef.current = Boolean(renderTooltip)
  }, [onPick, renderTooltip])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    let instance: MapLibreMap
    try {
      instance = new MapLibreMap({
        container,
        style: buildBasemapStyle(initialStyle.current.theme, initialStyle.current.basemap),
        bounds: initialView.current.bounds,
        fitBoundsOptions: { padding: initialView.current.padding },
        minZoom: 8.5,
        maxZoom: 16.5,
        attributionControl: false,
        dragRotate: false,
        pitchWithRotate: false,
        cooperativeGestures: false,
      })
    } catch (error) {
      queueMicrotask(() => setFailed(error instanceof Error ? error.message : 'WebGL indisponível'))
      return
    }
    instance.touchZoomRotate.disableRotation()
    instance.addControl(new AttributionControl({ compact: true }), 'bottom-right')
    const overlay = new MapboxOverlay({
      interleaved: false,
      layers: [],
      onClick: (info) => pickRef.current?.(info),
      onHover: (info) => {
        if (!tooltipEnabledRef.current) return
        setHover(
          info.object
            ? { x: info.x, y: info.y, width: info.viewport?.width ?? 0, object: info.object, layerId: info.layer?.id ?? '' }
            : null,
        )
      },
      getCursor: ({ isHovering, isDragging }) => (isDragging ? 'grabbing' : isHovering ? 'pointer' : 'grab'),
    })
    instance.addControl(overlay)
    mapRef.current = instance
    overlayRef.current = overlay
    queueMicrotask(() => setMap(instance))
    return () => {
      overlayRef.current = null
      mapRef.current = null
      instance.remove()
    }
  }, [])

  useEffect(() => {
    if (!map || !showNavigation) return
    const nav = new NavigationControl({ showCompass: false, visualizePitch: false })
    map.addControl(nav, 'bottom-right')
    return () => {
      map.removeControl(nav)
    }
  }, [map, showNavigation])

  useEffect(() => {
    overlayRef.current?.setProps({ layers })
  }, [layers, map])

  useEffect(() => {
    if (!map) return
    if (initialStyle.current.theme === theme && initialStyle.current.basemap === basemap) return
    initialStyle.current = { theme, basemap }
    map.setStyle(buildBasemapStyle(theme, basemap))
  }, [map, theme, basemap])

  useEffect(() => {
    if (!map || !sync) return
    return sync.register(map)
  }, [map, sync])

  if (failed) {
    return (
      <div className={cn('flex items-center justify-center bg-surface', className)} role="img" aria-label={ariaLabel}>
        <EmptyState icon={<MapPinOff />} title="Mapa indisponível" description={`O navegador não iniciou o WebGL (${failed}).`} />
      </div>
    )
  }

  return (
    <div
      className={cn('relative isolate overflow-hidden', className)}
      style={{ background: BASEMAP_COLORS[theme].land }}
      onMouseLeave={() => setHover(null)}
    >
      {/* Estilo inline: o CSS do MapLibre (fora das camadas do Tailwind) força position: relative. */}
      <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} role="region" aria-label={ariaLabel} />
      {children}
      {hover && renderTooltip ? (
        <div
          className="pointer-events-none absolute z-20 max-w-64 rounded-lg border border-line-strong bg-surface-raised px-2.5 py-2 text-xs text-fg shadow-panel"
          style={{ left: hover.width > 0 ? Math.min(hover.x + 14, hover.width - 264) : hover.x + 14, top: hover.y + 14 }}
        >
          {renderTooltip(hover)}
        </div>
      ) : null}
    </div>
  )
}
