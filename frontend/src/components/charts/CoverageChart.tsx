import { useMemo } from 'react'
import { formatDay, formatPercent } from '@/lib/format'
import { seriesHex } from '@/theme/colors'
import { useTheme } from '@/theme/ThemeProvider'
import type { AlgorithmId, DayResult } from '@/types'
import { baseOption, CHART_TOKENS, categoryAxis, tooltipRow, valueAxis } from './chartTheme'
import { EChart } from './EChart'

/** Cobertura simulada por dia — métrica de controle da comparação. */
export function CoverageChart({
  days,
  algorithms,
  names,
  height = 240,
}: {
  days: readonly DayResult[]
  algorithms: readonly AlgorithmId[]
  names: Record<AlgorithmId, string>
  height?: number
}) {
  const { theme } = useTheme()
  const option = useMemo(() => {
    const t = CHART_TOKENS[theme]
    const labels = days.map((d) => formatDay(d.date))
    const all = days.flatMap((d) => algorithms.map((id) => d.metrics[id].coverage ?? 0))
    const min = Math.max(0, Math.floor((Math.min(...all) - 0.03) * 20) / 20)
    return {
      ...baseOption(t),
      tooltip: {
        ...baseOption(t).tooltip,
        trigger: 'axis',
        axisPointer: { type: 'line', lineStyle: { color: t.axis } },
        formatter: (params: { dataIndex: number }[]) => {
          const i = params[0]?.dataIndex ?? 0
          const d = days[i]
          if (!d) return ''
          const rows = algorithms.map((id) => tooltipRow(seriesHex(theme, id), names[id], formatPercent(d.metrics[id].coverage))).join('')
          return `<div style="margin-bottom:6px;color:${t.text2}">${labels[i]} · cobertura simulada</div>${rows}`
        },
      },
      xAxis: { ...categoryAxis(t, labels), boundaryGap: false },
      yAxis: { ...valueAxis(t, (v: number) => `${Math.round(v * 100)}%`), min, max: 1 },
      series: algorithms.map((id) => ({
        name: names[id],
        type: 'line',
        data: days.map((d) => d.metrics[id].coverage),
        symbol: 'circle',
        symbolSize: 7,
        lineStyle: { width: 2, type: id === 'baseline' ? 'dashed' : 'solid', color: seriesHex(theme, id) },
        itemStyle: { color: seriesHex(theme, id), borderColor: t.surface, borderWidth: 1.5 },
        emphasis: { focus: 'series' },
      })),
    }
  }, [days, algorithms, names, theme])

  return <EChart option={option} height={height} ariaLabel="Gráfico de linhas da cobertura simulada por dia" />
}
