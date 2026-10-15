import type { AlgorithmId, VehicleState } from '@/types'
import type { Theme } from './ThemeProvider'

/** Cores em RGB para camadas WebGL (deck.gl) e gráficos. Espelham `styles/tokens.css`. */
export type RGB = [number, number, number]

const SERIES: Record<Theme, Record<AlgorithmId, RGB>> = {
  dark: {
    guloso: [57, 135, 229],
    proporcional: [217, 89, 38],
    atribuicao_otima: [25, 158, 112],
    baseline: [138, 144, 153],
  },
  light: {
    guloso: [42, 120, 214],
    proporcional: [235, 104, 52],
    atribuicao_otima: [27, 175, 122],
    baseline: [137, 135, 129],
  },
}

export function seriesRgb(theme: Theme, id: AlgorithmId): RGB {
  return SERIES[theme][id]
}

export function rgbToHex([r, g, b]: RGB): string {
  return `#${[r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('')}`
}

export function seriesHex(theme: Theme, id: AlgorithmId): string {
  return rgbToHex(seriesRgb(theme, id))
}

/** Classe Tailwind de fundo por estratégia (para legendas e chips). */
export const SERIES_BG: Record<AlgorithmId, string> = {
  guloso: 'bg-s-guloso',
  proporcional: 'bg-s-proporcional',
  atribuicao_otima: 'bg-s-atribuicao',
  baseline: 'bg-s-baseline',
}

export interface MapPalette {
  vehicle: Record<VehicleState, RGB>
  vehicleOutline: RGB
  requestServed: RGB
  requestUnserved: RGB
  requestWaiting: RGB
  pickupTrail: RGB
  tripTrail: RGB
  planned: RGB
  notExecuted: RGB
  /** Rampa sequencial (violeta) para demanda prevista; claro→escuro conforme o tema. */
  demandRamp: RGB[]
  heatRamp: RGB[]
}

export const MAP_PALETTE: Record<Theme, MapPalette> = {
  dark: {
    vehicle: {
      idle: [178, 184, 193],
      repositioning: [57, 135, 229],
      to_pickup: [255, 255, 255],
      on_trip: [110, 116, 125],
      unavailable: [70, 75, 83],
    },
    vehicleOutline: [7, 8, 10],
    requestServed: [162, 168, 177],
    requestUnserved: [208, 59, 59],
    requestWaiting: [250, 178, 25],
    pickupTrail: [236, 238, 241],
    tripTrail: [200, 205, 212],
    planned: [236, 238, 241],
    notExecuted: [120, 126, 135],
    demandRamp: [
      [44, 38, 82],
      [72, 58, 140],
      [104, 86, 196],
      [144, 133, 233],
      [189, 182, 246],
    ],
    heatRamp: [
      [31, 27, 58],
      [72, 58, 140],
      [120, 104, 214],
      [173, 160, 245],
      [222, 216, 255],
    ],
  },
  light: {
    vehicle: {
      idle: [92, 98, 107],
      repositioning: [42, 120, 214],
      to_pickup: [13, 15, 18],
      on_trip: [120, 126, 135],
      unavailable: [176, 180, 187],
    },
    vehicleOutline: [255, 255, 255],
    requestServed: [96, 102, 111],
    requestUnserved: [208, 59, 59],
    requestWaiting: [201, 133, 0],
    pickupTrail: [13, 15, 18],
    tripTrail: [90, 96, 105],
    planned: [13, 15, 18],
    notExecuted: [150, 155, 163],
    demandRamp: [
      [226, 223, 250],
      [196, 189, 244],
      [154, 141, 233],
      [111, 94, 205],
      [74, 58, 167],
    ],
    heatRamp: [
      [236, 234, 252],
      [196, 189, 244],
      [140, 125, 226],
      [92, 74, 190],
      [56, 42, 140],
    ],
  },
}

/** Interpola uma rampa discreta para t ∈ [0, 1]. */
export function rampColor(ramp: readonly RGB[], t: number): RGB {
  if (ramp.length === 0) return [128, 128, 128]
  const x = Math.min(1, Math.max(0, t)) * (ramp.length - 1)
  const i = Math.floor(x)
  const a = ramp[i]!
  const b = ramp[Math.min(ramp.length - 1, i + 1)]!
  const f = x - i
  return [Math.round(a[0] + (b[0] - a[0]) * f), Math.round(a[1] + (b[1] - a[1]) * f), Math.round(a[2] + (b[2] - a[2]) * f)]
}
