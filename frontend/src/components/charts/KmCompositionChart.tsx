import { useMemo } from 'react'
import { formatKm, formatNumber } from '@/lib/format'
import { seriesHex } from '@/theme/colors'
import { useTheme } from '@/theme/ThemeProvider'
import type { AlgorithmId, ScenarioMetrics } from '@/types'
import { baseOption, CHART_TOKENS, tooltipRow, valueAxis } from './chartTheme'
import { EChart } from './EChart'

/**
 * Composição do KM vazio por estratégia: pickup (neutro) + reposicionamento (cor da estratégia).
 * Deixa explícito que o reposicionamento entra no total (RN031).
 */
export function KmCompositionChart({
  metrics,
  algorithms,
  names,
  height = 210,
}: {
  metrics: Partial<Record<AlgorithmId, ScenarioMetrics>>
  algorithms: readonly AlgorithmId[]
  names: Record<AlgorithmId, string>
  height?: number
}) {
  const { theme } = useTheme()
  const option = useMemo(() => {
    const t = CHART_TOKENS[theme]
    const ids = [...algorithms].reverse()
    const rows = ids.map((id) => metrics[id])
    return {
      ...baseOption(t),
      grid: { left: 8, right: 56, top: 30, bottom: 4, containLabel: true },
      legend: {
        ...baseOption(t).legend,
        data: [
          { name: 'Pickup', itemStyle: { color: t.neutralBar } },
          { name: 'Reposicionamento', itemStyle: { color: t.text2 } },
        ],
      },
      tooltip: {
        ...baseOption(t).tooltip,
        trigger: 'axis',
        axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(127,127,127,0.06)' } },
        formatter: (params: { dataIndex: number }[]) => {
          const i = params[0]?.dataIndex ?? 0
          const id = ids[i]
          const m = rows[i]
          if (!id || !m) return ''
          return `<div style="margin-bottom:6px;color:${t.text2}">${names[id]}</div>
            ${tooltipRow(t.neutralBar, 'Pickup', formatKm(m.pickupKm))}
            ${tooltipRow(seriesHex(theme, id), 'Reposicionamento', formatKm(m.repositionKm))}
            ${tooltipRow('transparent', 'KM vazio total', formatKm(m.emptyKmTotal))}`
        },
      },
      xAxis: { ...valueAxis(t, (v: number) => formatNumber(v)), splitNumber: 3 },
      yAxis: {
        type: 'category',
        data: ids.map((id) => names[id]),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: t.text2, fontSize: 11 },
      },
      series: [
        {
          name: 'Pickup',
          type: 'bar',
          stack: 'km',
          barWidth: 14,
          data: rows.map((m) => (m ? Math.round(m.pickupKm) : 0)),
          itemStyle: { color: t.neutralBar, borderRadius: [4, 0, 0, 4], borderColor: t.surface, borderWidth: 1 },
        },
        {
          name: 'Reposicionamento',
          type: 'bar',
          stack: 'km',
          barWidth: 14,
          data: ids.map((id, i) => ({
            value: Math.round(rows[i]?.repositionKm ?? 0),
            itemStyle: { color: seriesHex(theme, id) },
          })),
          itemStyle: { borderRadius: [0, 4, 4, 0], borderColor: t.surface, borderWidth: 1 },
          label: {
            show: true,
            position: 'right',
            color: t.text2,
            fontSize: 10.5,
            formatter: (p: { dataIndex: number }) => formatNumber(rows[p.dataIndex]?.emptyKmTotal ?? 0),
          },
        },
      ],
    }
  }, [metrics, algorithms, names, theme])

  return <EChart option={option} height={height} ariaLabel="Barras empilhadas de pickup e reposicionamento por estratégia" />
}
