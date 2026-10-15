/** Utilitários de tempo. O fuso do estudo é America/Sao_Paulo (UTC−03:00, sem horário de verão). */
export const STUDY_TIMEZONE = 'America/Sao_Paulo'
export const STUDY_OFFSET = '-03:00'

export const MINUTE = 60_000
export const HOUR = 60 * MINUTE

/** Epoch de uma data local + minutos desde 00:00. */
export function localEpoch(date: string, minutesOfDay: number): number {
  return Date.parse(`${date}T00:00:00${STUDY_OFFSET}`) + Math.round(minutesOfDay * MINUTE)
}

/** Epoch → ISO com deslocamento −03:00 (estável e legível). */
export function toIso(epochMs: number): string {
  const shifted = new Date(epochMs - 3 * HOUR)
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${shifted.getUTCFullYear()}-${pad(shifted.getUTCMonth() + 1)}-${pad(shifted.getUTCDate())}` +
    `T${pad(shifted.getUTCHours())}:${pad(shifted.getUTCMinutes())}:${pad(shifted.getUTCSeconds())}${STUDY_OFFSET}`
  )
}

export function toEpoch(iso: string): number {
  const value = Date.parse(iso)
  if (Number.isNaN(value)) throw new Error(`Data inválida: ${iso}`)
  return value
}

export function addDays(date: string, days: number): string {
  const d = new Date(`${date}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}
