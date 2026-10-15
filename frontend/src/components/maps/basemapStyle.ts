import type { ExpressionSpecification, LayerSpecification, StyleSpecification } from 'maplibre-gl'
import type { Theme } from '@/theme/ThemeProvider'

/**
 * Estilo cartográfico minimalista do FleetLab sobre tiles vetoriais públicos do OpenFreeMap
 * (esquema OpenMapTiles, dados OpenStreetMap). Não exige token nem conta. Sem rede, o mapa
 * continua funcional com fundo liso e as camadas de dados.
 */
export const OPENFREEMAP_TILEJSON = 'https://tiles.openfreemap.org/planet'
export const OPENFREEMAP_GLYPHS = 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf'

interface BasemapColors {
  land: string
  water: string
  park: string
  roadMinor: string
  roadMajor: string
  roadMotorway: string
  boundary: string
  building: string
  label: string
  labelStrong: string
  halo: string
}

export const BASEMAP_COLORS: Record<Theme, BasemapColors> = {
  dark: {
    land: '#121519',
    water: '#06090e',
    park: '#121811',
    roadMinor: '#1b1f25',
    roadMajor: '#272c34',
    roadMotorway: '#333944',
    boundary: '#3a404a',
    building: '#161a1f',
    label: '#68707b',
    labelStrong: '#9aa1ab',
    halo: '#121519',
  },
  light: {
    land: '#f3f3f1',
    water: '#d9e1e8',
    park: '#e8ede4',
    roadMinor: '#ffffff',
    roadMajor: '#e3e5e8',
    roadMotorway: '#d5d8dd',
    boundary: '#b9bec6',
    building: '#e8e8e5',
    label: '#8a9098',
    labelStrong: '#4d535b',
    halo: '#f3f3f1',
  },
}

const name: ExpressionSpecification = ['coalesce', ['get', 'name:pt'], ['get', 'name']]

function roadWidth(base: number, max: number): ExpressionSpecification {
  return ['interpolate', ['exponential', 1.5], ['zoom'], 8, base, 13, base * 3, 17, max]
}

function vectorLayers(c: BasemapColors): LayerSpecification[] {
  const src = 'openmaptiles'
  return [
    { id: 'park', type: 'fill', source: src, 'source-layer': 'park', paint: { 'fill-color': c.park, 'fill-opacity': 0.8 } },
    {
      id: 'landcover-wood',
      type: 'fill',
      source: src,
      'source-layer': 'landcover',
      filter: ['in', ['get', 'class'], ['literal', ['wood', 'grass']]],
      paint: { 'fill-color': c.park, 'fill-opacity': 0.5 },
    },
    { id: 'water', type: 'fill', source: src, 'source-layer': 'water', paint: { 'fill-color': c.water } },
    {
      id: 'building',
      type: 'fill',
      source: src,
      'source-layer': 'building',
      minzoom: 14,
      paint: { 'fill-color': c.building, 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 14, 0, 15, 0.8] },
    },
    {
      id: 'aeroway',
      type: 'line',
      source: src,
      'source-layer': 'aeroway',
      filter: ['==', ['get', 'class'], 'runway'],
      paint: { 'line-color': c.roadMajor, 'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1, 15, 12] },
    },
    {
      id: 'road-minor',
      type: 'line',
      source: src,
      'source-layer': 'transportation',
      minzoom: 12.5,
      filter: ['in', ['get', 'class'], ['literal', ['minor', 'service', 'track']]],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': c.roadMinor, 'line-width': roadWidth(0.3, 6) },
    },
    {
      id: 'road-secondary',
      type: 'line',
      source: src,
      'source-layer': 'transportation',
      minzoom: 10,
      filter: ['in', ['get', 'class'], ['literal', ['secondary', 'tertiary']]],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': c.roadMajor, 'line-width': roadWidth(0.4, 9) },
    },
    {
      id: 'road-primary',
      type: 'line',
      source: src,
      'source-layer': 'transportation',
      filter: ['in', ['get', 'class'], ['literal', ['primary', 'trunk']]],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': c.roadMajor, 'line-width': roadWidth(0.6, 12) },
    },
    {
      id: 'road-motorway',
      type: 'line',
      source: src,
      'source-layer': 'transportation',
      filter: ['==', ['get', 'class'], 'motorway'],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': c.roadMotorway, 'line-width': roadWidth(0.8, 14) },
    },
    {
      id: 'boundary-municipal',
      type: 'line',
      source: src,
      'source-layer': 'boundary',
      filter: ['all', ['==', ['get', 'admin_level'], 8], ['!=', ['get', 'maritime'], 1]],
      paint: { 'line-color': c.boundary, 'line-width': 0.8, 'line-dasharray': [3, 3] },
    },
    {
      id: 'place-neighbourhood',
      type: 'symbol',
      source: src,
      'source-layer': 'place',
      minzoom: 12.5,
      filter: ['in', ['get', 'class'], ['literal', ['suburb', 'neighbourhood', 'quarter']]],
      layout: {
        'text-field': name,
        'text-font': ['Noto Sans Regular'],
        'text-size': 10.5,
        'text-max-width': 8,
      },
      paint: { 'text-color': c.label, 'text-halo-color': c.halo, 'text-halo-width': 1.2 },
    },
    {
      id: 'place-city',
      type: 'symbol',
      source: src,
      'source-layer': 'place',
      filter: ['in', ['get', 'class'], ['literal', ['city', 'town']]],
      layout: {
        'text-field': name,
        'text-font': ['Noto Sans Bold'],
        'text-size': ['interpolate', ['linear'], ['zoom'], 9, 10, 13, 13],
        'text-transform': 'uppercase',
        'text-letter-spacing': 0.12,
      },
      paint: { 'text-color': c.labelStrong, 'text-halo-color': c.halo, 'text-halo-width': 1.5 },
    },
  ]
}

export function buildBasemapStyle(theme: Theme, showBasemap: boolean): StyleSpecification {
  const c = BASEMAP_COLORS[theme]
  return {
    version: 8,
    name: `fleetlab-${theme}`,
    glyphs: OPENFREEMAP_GLYPHS,
    sources: showBasemap ? { openmaptiles: { type: 'vector', url: OPENFREEMAP_TILEJSON } } : {},
    layers: [
      { id: 'background', type: 'background', paint: { 'background-color': c.land } },
      ...(showBasemap ? vectorLayers(c) : []),
    ],
  }
}
