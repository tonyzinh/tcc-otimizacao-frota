import { useMemo } from 'react'
import { formatDay, formatKm, formatNumber } from '@/lib/format'
import { seriesHex } from '@/theme/colors'
import { useTheme } from '@/theme/ThemeProvider'
import type { AlgorithmId, DayResult } from '@/types'
import { baseOption, CHART_TOKENS, categoryAxis, tooltipRow, valueAxis } from './chartTheme'
import { EChart } from './EChart'

/** KM vazio estimado (pickup + reposicionamento) por dia e estratégia. */
export function DailyEmptyKmChart({
  days,
  algorithms,
  names,
  height = 260,
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
    return {
      ...baseOption(t),
      tooltip: {
        ...baseOption(t).tooltip,
        trigger: 'axis',
        axisPointer: { type: 'line', lineStyle: { color: t.axis } },
        formatter: (params: { dataIndex: number }[]) => {
          const i = params[0]?.dataIndex ?? 0
          const day = days[i]
          if (!day) return ''
          const rows = algorithms
            .map((id) => tooltipRow(seriesHex(theme, id), names[id], formatKm(day.metrics[id].emptyKmTotal)))
            .join('')
          return `<div style="margin-bottom:6px;color:${t.text2}">${labels[i]} · KM vazio estimado</div>${rows}`
        },
      },
      xAxis: { ...categoryAxis(t, labels), boundaryGap: false },
      yAxis: valueAxis(t, (v: number) => formatNumber(v)),
      series: algorithms.map((id) => ({
        name: names[id],
        type: 'line',
        data: days.map((d) => Math.round(d.metrics[id].emptyKmTotal * 10) / 10),
        symbol: 'circle',
        symbolSize: 7,
        showSymbol: true,
        lineStyle: { width: 2, type: id === 'baseline' ? 'dashed' : 'solid', color: seriesHex(theme, id) },
        itemStyle: { color: seriesHex(theme, id), borderColor: t.surface, borderWidth: 1.5 },
        emphasis: { focus: 'series' },
        z: id === 'baseline' ? 1 : 2,
      })),
    }
  }, [days, algorithms, names, theme])

  return <EChart option={option} height={height} ariaLabel="Gráfico de linhas do KM vazio estimado por dia e estratégia" />
}
