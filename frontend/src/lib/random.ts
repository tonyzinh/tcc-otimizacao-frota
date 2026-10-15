/** PRNG determinístico (mulberry32) para que os dados demonstrativos sejam reprodutíveis. */
export type Rng = () => number

export function hashString(value: string): number {
  let h = 2166136261
  for (let i = 0; i < value.length; i += 1) {
    h ^= value.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}

export function createRng(seed: number | string): Rng {
  let a = typeof seed === 'string' ? hashString(seed) : seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export function uniform(rng: Rng, min: number, max: number): number {
  return min + (max - min) * rng()
}

/** Normal por Box–Muller. */
export function normal(rng: Rng, mean = 0, sd = 1): number {
  const u = Math.max(rng(), 1e-12)
  const v = rng()
  return mean + sd * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
}

/** Amostra de Poisson (Knuth para médias pequenas, aproximação normal acima de 30). */
export function poisson(rng: Rng, mean: number): number {
  if (mean <= 0) return 0
  if (mean > 30) return Math.max(0, Math.round(normal(rng, mean, Math.sqrt(mean))))
  const limit = Math.exp(-mean)
  let k = 0
  let p = 1
  do {
    k += 1
    p *= rng()
  } while (p > limit)
  return k - 1
}

export function pickWeighted<T>(rng: Rng, items: readonly T[], weight: (item: T) => number): T {
  if (items.length === 0) throw new Error('pickWeighted: lista vazia')
  const total = items.reduce((sum, item) => sum + Math.max(0, weight(item)), 0)
  if (total <= 0) return items[Math.floor(rng() * items.length)]!
  let r = rng() * total
  for (const item of items) {
    r -= Math.max(0, weight(item))
    if (r <= 0) return item
  }
  return items[items.length - 1]!
}
