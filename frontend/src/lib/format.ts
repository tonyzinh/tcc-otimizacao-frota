import { STUDY_TIMEZONE } from './time'

const LOCALE = 'pt-BR'

const timeFmt = new Intl.DateTimeFormat(LOCALE, { timeZone: STUDY_TIMEZONE, hour: '2-digit', minute: '2-digit' })
const timeSecFmt = new Intl.DateTimeFormat(LOCALE, {
  timeZone: STUDY_TIMEZONE,
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
})
const dayFmt = new Intl.DateTimeFormat(LOCALE, { timeZone: 'UTC', weekday: 'short', day: '2-digit', month: '2-digit' })
const longDayFmt = new Intl.DateTimeFormat(LOCALE, {
  timeZone: 'UTC',
  weekday: 'long',
  day: '2-digit',
  month: 'long',
  year: 'numeric',
})

export function formatNumber(value: number, digits = 0): string {
  return value.toLocaleString(LOCALE, { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export function formatKm(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—'
  return `${formatNumber(value, digits)} km`
}

/** Fração 0–1 → "93,3%". */
export function formatPercent(fraction: number | null | undefined, digits = 1): string {
  if (fraction === null || fraction === undefined || !Number.isFinite(fraction)) return '—'
  return `${formatNumber(fraction * 100, digits)}%`
}

function isZero(value: number, digits: number): boolean {
  return Math.abs(value) < 0.5 * 10 ** -digits
}

/** Valor já em pontos percentuais, com sinal explícito: "+4,2%" / "−3,1%". */
export function formatSignedPercent(points: number | null | undefined, digits = 1): string {
  if (points === null || points === undefined || !Number.isFinite(points)) return '—'
  if (isZero(points, digits)) return `${formatNumber(0, digits)}%`
  return `${points > 0 ? '+' : '−'}${formatNumber(Math.abs(points), digits)}%`
}

export function formatSignedKm(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—'
  if (isZero(value, digits)) return `${formatNumber(0, digits)} km`
  return `${value > 0 ? '+' : '−'}${formatNumber(Math.abs(value), digits)} km`
}

/** Diferença em pontos percentuais a partir de frações: 0,012 → "+1,2 p.p.". */
export function formatSignedPoints(fraction: number | null | undefined, digits = 1): string {
  if (fraction === null || fraction === undefined || !Number.isFinite(fraction)) return '—'
  const points = fraction * 100
  if (isZero(points, digits)) return `${formatNumber(0, digits)} p.p.`
  return `${points > 0 ? '+' : '−'}${formatNumber(Math.abs(points), digits)} p.p.`
}

export function formatMinutes(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—'
  return `${formatNumber(value, digits)} min`
}

export function formatClock(epochMs: number, withSeconds = false): string {
  return (withSeconds ? timeSecFmt : timeFmt).format(new Date(epochMs))
}

/** "seg, 07/01" a partir de YYYY-MM-DD. */
export function formatDay(date: string): string {
  return dayFmt.format(new Date(`${date}T12:00:00Z`)).replace('.', '')
}

export function formatLongDay(date: string): string {
  return longDayFmt.format(new Date(`${date}T12:00:00Z`))
}
