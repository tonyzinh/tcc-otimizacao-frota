import type { LngLat } from '@/types'

const EARTH_RADIUS_KM = 6371.0088

const rad = (deg: number) => (deg * Math.PI) / 180

/** Distância geodésica (Haversine) em km — o mesmo método rotulado como estimativa no TCC. */
export function haversineKm(a: LngLat, b: LngLat): number {
  const dLat = rad(b[1] - a[1])
  const dLng = rad(b[0] - a[0])
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a[1])) * Math.cos(rad(b[1])) * Math.sin(dLng / 2) ** 2
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.min(1, Math.sqrt(h)))
}

/** Desloca um ponto por (leste, norte) em km — aproximação local, suficiente para dados demo. */
export function offsetKm(origin: LngLat, eastKm: number, northKm: number): LngLat {
  const dLat = northKm / 110.574
  const dLng = eastKm / (111.32 * Math.cos(rad(origin[1])))
  return [origin[0] + dLng, origin[1] + dLat]
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t
}

export function lerpLngLat(a: LngLat, b: LngLat, t: number): LngLat {
  return [lerp(a[0], b[0], t), lerp(a[1], b[1], t)]
}

/**
 * Curva quadrática entre dois pontos, usada SOMENTE como geometria ilustrativa de trajetos.
 * Não representa rota viária e não altera nenhuma distância reportada.
 */
export function illustrativeCurve(from: LngLat, to: LngLat, bend: number, steps = 18): LngLat[] {
  const mid = lerpLngLat(from, to, 0.5)
  const dx = to[0] - from[0]
  const dy = to[1] - from[1]
  const control: LngLat = [mid[0] - dy * bend, mid[1] + dx * bend]
  const points: LngLat[] = []
  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps
    const u = 1 - t
    points.push([
      u * u * from[0] + 2 * u * t * control[0] + t * t * to[0],
      u * u * from[1] + 2 * u * t * control[1] + t * t * to[1],
    ])
  }
  return points
}

/** Comprimentos acumulados (km) ao longo de uma polilinha. */
export function cumulativeLengths(path: readonly LngLat[]): number[] {
  const out = [0]
  for (let i = 1; i < path.length; i += 1) {
    out.push(out[i - 1]! + haversineKm(path[i - 1]!, path[i]!))
  }
  return out
}

/** Ponto na fração `t` (0–1) do comprimento da polilinha. */
export function pointAlong(path: readonly LngLat[], lengths: readonly number[], t: number): LngLat {
  if (path.length === 0) throw new Error('pointAlong: caminho vazio')
  if (path.length === 1 || t <= 0) return path[0]!
  const total = lengths[lengths.length - 1]!
  if (t >= 1 || total === 0) return path[path.length - 1]!
  const target = total * t
  let lo = 0
  let hi = lengths.length - 1
  while (lo < hi - 1) {
    const mid = (lo + hi) >> 1
    if (lengths[mid]! <= target) lo = mid
    else hi = mid
  }
  const segLen = lengths[hi]! - lengths[lo]!
  const local = segLen === 0 ? 0 : (target - lengths[lo]!) / segLen
  return lerpLngLat(path[lo]!, path[hi]!, local)
}
