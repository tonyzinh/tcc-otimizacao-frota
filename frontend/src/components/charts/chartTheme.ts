import type { Theme } from '@/theme/ThemeProvider'

/** Tokens dos gráficos — espelham `styles/tokens.css` (ink, grade e eixos recessivos). */
export interface ChartTokens {
  surface: string
  surfaceRaised: string
  borderStrong: string
  text1: string
  text2: string
  text3: string
  grid: string
  axis: string
  neutralBar: string
  zeroLine: string
}

export const CHART_TOKENS: Record<Theme, ChartTokens> = {
  dark: {
    surface: '#0d0f12',
    surfaceRaised: '#13161a',
    borderStrong: 'rgba(255,255,255,0.13)',
    text1: '#eceef1',
    text2: '#a2a8b1',
    text3: '#6b727c',
    grid: '#1c1f24',
    axis: '#383d44',
    neutralBar: '#4b515a',
    zeroLine: '#6b727c',
  },
  light: {
    surface: '#ffffff',
    surfaceRaised: '#ffffff',
    borderStrong: 'rgba(12,14,18,0.15)',
    text1: '#0d0f12',
    text2: '#4b515a',
    text3: '#80868f',
    grid: '#eef0f2',
    axis: '#c5c8ce',
    neutralBar: '#b7bcc4',
    zeroLine: '#80868f',
  },
}

const FONT = "'Inter Variable', ui-sans-serif, system-ui, sans-serif"

export function baseOption(tokens: ChartTokens) {
  return {
    animationDuration: 450,
    animationEasing: 'cubicOut' as const,
    textStyle: { fontFamily: FONT, color: tokens.text2, fontSize: 11 },
    grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
    legend: {
      top: 0,
      left: 0,
      icon: 'roundRect',
      itemWidth: 10,
      itemHeight: 3,
      itemGap: 14,
      textStyle: { color: tokens.text2, fontSize: 11, fontFamily: FONT },
      inactiveColor: tokens.axis,
    },
    tooltip: {
      backgroundColor: tokens.surfaceRaised,
      borderColor: tokens.borderStrong,
      borderWidth: 1,
      padding: [8, 10],
      textStyle: { color: tokens.text1, fontSize: 12, fontFamily: FONT },
      extraCssText: 'border-radius:8px; box-shadow: 0 12px 32px -12px rgba(0,0,0,.45);',
      confine: true,
    },
  }
}

export function valueAxis(tokens: ChartTokens, formatter?: (v: number) => string) {
  return {
    type: 'value' as const,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: tokens.grid, width: 1 } },
    axisLabel: { color: tokens.text3, fontSize: 10.5, formatter },
  }
}

export function categoryAxis(tokens: ChartTokens, data: string[]) {
  return {
    type: 'category' as const,
    data,
    axisLine: { lineStyle: { color: tokens.axis } },
    axisTick: { show: false },
    axisLabel: { color: tokens.text3, fontSize: 10.5 },
  }
}

/** Linha de tooltip com marcador de série (identidade nunca só pela cor: sempre com nome). */
export function tooltipRow(color: string, label: string, value: string): string {
  return `<div style="display:flex;align-items:center;gap:8px;justify-content:space-between;min-width:180px">
    <span style="display:flex;align-items:center;gap:6px"><span style="width:8px;height:8px;border-radius:2px;background:${color}"></span>${label}</span>
    <span style="font-variant-numeric:tabular-nums;font-weight:500">${value}</span></div>`
}
