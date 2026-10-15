import { useMemo } from 'react'
import { formatDay, formatNumber } from '@/lib/format'
import { useTheme } from '@/theme/ThemeProvider'
import type { DayResult } from '@/types'
import { baseOption, CHART_TOKENS, categoryAxis, tooltipRow, valueAxis } from './chartTheme'
import { EChart } from './EChart'

const DEMAND = { dark: '#9085e9', light: '#4a3aa7' } as const

/** Pedidos previstos no corte × observados no replay (mesma unidade, um único eixo). */
export function DemandChart({ days, height = 220 }: { days: readonly DayResult[]; height?: number }) {
  const { theme } = useTheme()
  const option = useMemo(() => {
    const t = CHART_TOKENS[theme]
    const labels = days.map((d) => formatDay(d.date))
    const color = DEMAND[theme]
    return {
      ...baseOption(t),
      legend: {
        ...baseOption(t).legend,
        data: [
          { name: 'Observados (D+1)', itemStyle: { color } },
          { name: 'Previstos no corte', itemStyle: { color: t.text1 } },
        ],
      },
      tooltip: {
        ...baseOption(t).tooltip,
        trigger: 'axis',
        axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(127,127,127,0.06)' } },
        formatter: (params: { dataIndex: number }[]) => {
          const i = params[0]?.dataIndex ?? 0
          const d = days[i]
          if (!d) return ''
          return `<div style="margin-bottom:6px;color:${t.text2}">${labels[i]}</div>
            ${tooltipRow(color, 'Observados (D+1)', formatNumber(d.observedTotal))}
            ${tooltipRow(t.text1, 'Previstos no corte', formatNumber(d.forecastTotal, 1))}`
        },
      },
      xAxis: categoryAxis(t, labels),
      yAxis: valueAxis(t, (v: number) => formatNumber(v)),
      series: [
        {
          name: 'Observados (D+1)',
          type: 'bar',
          barWidth: '46%',
          data: days.map((d) => d.observedTotal),
          itemStyle: { color, borderRadius: [4, 4, 0, 0] },
        },
        {
          name: 'Previstos no corte',
          type: 'line',
          data: days.map((d) => Math.round(d.forecastTotal * 10) / 10),
          symbol: 'circle',
          symbolSize: 7,
          lineStyle: { width: 2, color: t.text1 },
          itemStyle: { color: t.text1, borderColor: t.surface, borderWidth: 1.5 },
        },
      ],
    }
  }, [days, theme])

  return <EChart option={option} height={height} ariaLabel="Pedidos previstos no corte e observados por dia" />
}
