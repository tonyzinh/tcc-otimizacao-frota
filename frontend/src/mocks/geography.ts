/**
 * Geografia demonstrativa da Grande Vitória (ES).
 *
 * Usa apenas coordenadas públicas e aproximadas de bairros/sedes municipais. Os pesos abaixo são
 * FICTÍCIOS: servem para gerar padrões visuais plausíveis e não vêm de dados da empresa.
 */
import { offsetKm } from '@/lib/geo'
import type { Rng } from '@/lib/random'
import { normal } from '@/lib/random'
import type { LngLat } from '@/types'

export interface Locality {
  id: string
  name: string
  municipality: 'Vitória' | 'Vila Velha' | 'Serra' | 'Cariacica' | 'Viana'
  center: LngLat
  /** Peso fictício como origem de viagens na janela da manhã. */
  morningOrigin: number
  /** Peso fictício como destino na janela da manhã. */
  morningDestination: number
  /** Peso fictício de posição típica da frota no início da manhã. */
  fleetHome: number
  spreadKm: number
}

export const GRANDE_VITORIA_CENTER: LngLat = [-40.318, -20.285]

export const GRANDE_VITORIA_BOUNDS = {
  west: -40.56,
  south: -20.47,
  east: -40.15,
  north: -20.1,
} as const

export const LOCALITIES: readonly Locality[] = [
  { id: 'vix-centro', name: 'Centro', municipality: 'Vitória', center: [-40.338, -20.3195], morningOrigin: 0.4, morningDestination: 1.0, fleetHome: 0.5, spreadKm: 1.1 },
  { id: 'praia-canto', name: 'Praia do Canto', municipality: 'Vitória', center: [-40.2955, -20.2955], morningOrigin: 0.6, morningDestination: 0.8, fleetHome: 0.3, spreadKm: 1.0 },
  { id: 'enseada', name: 'Enseada do Suá', municipality: 'Vitória', center: [-40.2985, -20.3125], morningOrigin: 0.3, morningDestination: 0.9, fleetHome: 0.2, spreadKm: 0.8 },
  { id: 'jd-camburi', name: 'Jardim Camburi', municipality: 'Vitória', center: [-40.2715, -20.2615], morningOrigin: 0.8, morningDestination: 0.3, fleetHome: 0.3, spreadKm: 1.1 },
  { id: 'goiabeiras', name: 'Goiabeiras', municipality: 'Vitória', center: [-40.3055, -20.2785], morningOrigin: 0.3, morningDestination: 0.6, fleetHome: 0.2, spreadKm: 1.0 },
  { id: 'maruipe', name: 'Maruípe', municipality: 'Vitória', center: [-40.3185, -20.3005], morningOrigin: 0.4, morningDestination: 0.3, fleetHome: 0.3, spreadKm: 0.9 },
  { id: 'praia-costa', name: 'Praia da Costa', municipality: 'Vila Velha', center: [-40.2905, -20.3355], morningOrigin: 0.7, morningDestination: 0.4, fleetHome: 0.3, spreadKm: 0.9 },
  { id: 'gloria', name: 'Glória', municipality: 'Vila Velha', center: [-40.3175, -20.3365], morningOrigin: 0.5, morningDestination: 0.2, fleetHome: 0.6, spreadKm: 1.0 },
  { id: 'itaparica', name: 'Itaparica', municipality: 'Vila Velha', center: [-40.3095, -20.3645], morningOrigin: 0.7, morningDestination: 0.15, fleetHome: 0.4, spreadKm: 1.2 },
  { id: 'cobilandia', name: 'Cobilândia', municipality: 'Vila Velha', center: [-40.3525, -20.3505], morningOrigin: 0.4, morningDestination: 0.1, fleetHome: 0.7, spreadKm: 1.1 },
  { id: 'terra-vermelha', name: 'Terra Vermelha', municipality: 'Vila Velha', center: [-40.3385, -20.4115], morningOrigin: 0.45, morningDestination: 0.1, fleetHome: 0.5, spreadKm: 1.4 },
  { id: 'campo-grande', name: 'Campo Grande', municipality: 'Cariacica', center: [-40.3795, -20.3385], morningOrigin: 0.8, morningDestination: 0.3, fleetHome: 0.9, spreadKm: 1.2 },
  { id: 'itaciba', name: 'Itacibá', municipality: 'Cariacica', center: [-40.3565, -20.3305], morningOrigin: 0.4, morningDestination: 0.1, fleetHome: 0.6, spreadKm: 0.9 },
  { id: 'cariacica-sede', name: 'Cariacica Sede', municipality: 'Cariacica', center: [-40.4175, -20.2645], morningOrigin: 0.35, morningDestination: 0.1, fleetHome: 0.5, spreadKm: 1.3 },
  { id: 'laranjeiras', name: 'Laranjeiras', municipality: 'Serra', center: [-40.2575, -20.1965], morningOrigin: 1.0, morningDestination: 0.4, fleetHome: 0.6, spreadKm: 1.3 },
  { id: 'carapina', name: 'Carapina', municipality: 'Serra', center: [-40.2665, -20.2205], morningOrigin: 0.6, morningDestination: 0.4, fleetHome: 0.4, spreadKm: 1.2 },
  { id: 'jacaraipe', name: 'Jacaraípe', municipality: 'Serra', center: [-40.2045, -20.1515], morningOrigin: 0.6, morningDestination: 0.1, fleetHome: 0.3, spreadKm: 1.3 },
  { id: 'serra-sede', name: 'Serra Sede', municipality: 'Serra', center: [-40.3075, -20.1295], morningOrigin: 0.35, morningDestination: 0.1, fleetHome: 0.4, spreadKm: 1.3 },
  { id: 'viana', name: 'Viana', municipality: 'Viana', center: [-40.4955, -20.3905], morningOrigin: 0.25, morningDestination: 0.05, fleetHome: 0.4, spreadKm: 1.4 },
]

/**
 * Linha de costa simplificada (latitude → longitude limite a leste), de sul para norte.
 * Serve só para não gerar pontos demonstrativos no mar.
 */
const COAST: readonly (readonly [number, number])[] = [
  [-20.52, -40.38],
  [-20.47, -40.35],
  [-20.43, -40.326],
  [-20.4, -40.307],
  [-20.37, -40.298],
  [-20.35, -40.284],
  [-20.335, -40.28],
  [-20.322, -40.287],
  [-20.305, -40.287],
  [-20.29, -40.284],
  [-20.28, -40.276],
  [-20.27, -40.263],
  [-20.255, -40.251],
  [-20.24, -40.24],
  [-20.22, -40.228],
  [-20.2, -40.215],
  [-20.18, -40.2],
  [-20.16, -40.188],
  [-20.14, -40.178],
  [-20.12, -40.168],
  [-20.08, -40.15],
]

export function coastLongitude(lat: number): number {
  const first = COAST[0]!
  const last = COAST[COAST.length - 1]!
  if (lat <= first[0]) return first[1]
  if (lat >= last[0]) return last[1]
  for (let i = 1; i < COAST.length; i += 1) {
    const a = COAST[i - 1]!
    const b = COAST[i]!
    if (lat <= b[0]) {
      const t = (lat - a[0]) / (b[0] - a[0])
      return a[1] + (b[1] - a[1]) * t
    }
  }
  return last[1]
}

/** Canal entre a ilha de Vitória e Vila Velha/Cariacica (aproximação retangular). */
function inVitoriaBay([lng, lat]: LngLat): boolean {
  return lat < -20.3205 && lat > -20.3265 && lng > -40.372 && lng < -40.29
}

export function isOnLand(point: LngLat): boolean {
  const [lng, lat] = point
  const b = GRANDE_VITORIA_BOUNDS
  if (lng < b.west || lng > b.east || lat < b.south || lat > b.north) return false
  if (inVitoriaBay(point)) return false
  return lng < coastLongitude(lat) - 0.004
}

/** Ponto aleatório perto de `center`, garantidamente em terra (cai para `center` se falhar). */
export function jitterOnLand(rng: Rng, center: LngLat, spreadKm: number, attempts = 8): LngLat {
  for (let i = 0; i < attempts; i += 1) {
    const p = offsetKm(center, normal(rng, 0, spreadKm), normal(rng, 0, spreadKm))
    if (isOnLand(p)) return p
  }
  return center
}
