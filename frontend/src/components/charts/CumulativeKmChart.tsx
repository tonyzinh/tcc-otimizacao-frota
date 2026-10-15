import { useMemo } from 'react'
import { formatClock, formatKm, formatNumber } from '@/lib/format'
import { seriesHex } from '@/theme/colors'
import { useTheme } from '@/theme/ThemeProvider'
import type { AlgorithmId } from '@/types'
import { baseOption, CHART_TOKENS, tooltipRow, valueAxis } from './chartTheme'
import { EChart } from './EChart'

export interface CumulativeSeries {
  algorithmId: AlgorithmId
  name: string
  points: { t: number; emptyKm: number }[]
}

/** KM vazio acumulado ao longo do replay, com cursor no instante atual. */
export function CumulativeKmChart({
  series,
  playhead,
  height = 170,
}: {
  series: readonly CumulativeSeries[]
  playhead: number
  height?: number
}) {
  const { theme } = useTheme()
  // O cursor muda a cada quadro; o gráfico só precisa de atualizações a cada 30 s simulados.
  const bucket = Math.floor(playhead / 30_000) * 30_000
  const option = useMemo(() => {
    const t = CHART_TOKENS[theme]
    return {
      ...baseOption(t),
      animation: false,
      grid: { left: 4, right: 12, top: 30, bottom: 4, containLabel: true },
      tooltip: {
        ...baseOption(t).tooltip,
        trigger: 'axis',
        axisPointer: { type: 'line', lineStyle: { color: t.axis } },
        formatter: (params: { dataIndex: number; seriesIndex: number }[]) => {
          const i = params[0]?.dataIndex ?? 0
          const time = series[0]?.points[i]?.t
          if (time === undefined) return ''
          const rows = series
            .map((s) => tooltipRow(seriesHex(theme, s.algorithmId), s.name, formatKm(s.points[i]?.emptyKm ?? 0)))
            .join('')
          return `<div style="margin-bottom:6px;color:${t.text2}">${formatClock(time)} · KM vazio acumulado</div>${rows}`
        },
      },
      xAxis: {
        type: 'time',
        axisLine: { lineStyle: { color: t.axis } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { color: t.text3, fontSize: 10.5, formatter: (v: number) => formatClock(v) },
      },
      yAxis: valueAxis(t, (v: number) => formatNumber(v)),
      series: series.map((s, index) => ({
        name: s.name,
        type: 'line',
        showSymbol: false,
        data: s.points.map((p) => [p.t, Math.round(p.emptyKm * 10) / 10]),
        lineStyle: { width: 2, color: seriesHex(theme, s.algorithmId), type: s.algorithmId === 'baseline' ? 'dashed' : 'solid' },
        itemStyle: { color: seriesHex(theme, s.algorithmId) },
        markLine:
          index === 0
            ? {
                silent: true,
                symbol: 'none',
                animation: false,
                label: { show: false },
                lineStyle: { color: t.text1, width: 1, type: 'solid' },
                data: [{ xAxis: bucket }],
              }
            : undefined,
      })),
    }
  }, [series, bucket, theme])

  return <EChart option={option} height={height} ariaLabel="KM vazio acumulado ao longo do replay" />
}
