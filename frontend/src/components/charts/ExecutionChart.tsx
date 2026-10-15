import { useMemo } from 'react'
import { formatNumber, formatPercent } from '@/lib/format'
import { EXECUTION_OUTCOMES } from '@/lib/metrics'
import { useTheme } from '@/theme/ThemeProvider'
import { OUTCOME_LABELS } from '@/features/shared/labels'
import type { AlgorithmId, ExecutionOutcome, ScenarioMetrics } from '@/types'
import { baseOption, CHART_TOKENS, tooltipRow } from './chartTheme'
import { EChart } from './EChart'

/** Rampa ordinal neutra: executada em destaque, motivos de não execução em cinzas. */
function outcomeColors(dark: boolean): Record<ExecutionOutcome, string> {
  return dark
    ? { executed: '#eceef1', driver_absent: '#6b727c', driver_on_trip: '#4b515a', availability_conflict: '#30353c' }
    : { executed: '#0d0f12', driver_absent: '#80868f', driver_on_trip: '#aeb3ba', availability_conflict: '#d3d6db' }
}

/** Desfecho das recomendações planejadas (100% empilhado por estratégia). */
export function ExecutionChart({
  metrics,
  algorithms,
  names,
  height = 180,
}: {
  metrics: Partial<Record<AlgorithmId, ScenarioMetrics>>
  algorithms: readonly AlgorithmId[]
  names: Record<AlgorithmId, string>
  height?: number
}) {
  const { theme } = useTheme()
  const option = useMemo(() => {
    const t = CHART_TOKENS[theme]
    const colors = outcomeColors(theme === 'dark')
    const ids = [...algorithms].reverse()
    const share = (id: AlgorithmId, o: ExecutionOutcome) => {
      const m = metrics[id]
      return m && m.plannedMoves > 0 ? m.execution[o] / m.plannedMoves : 0
    }
    return {
      ...baseOption(t),
      grid: { left: 8, right: 12, top: 34, bottom: 4, containLabel: true },
      legend: { ...baseOption(t).legend, data: EXECUTION_OUTCOMES.map((o) => OUTCOME_LABELS[o]) },
      tooltip: {
        ...baseOption(t).tooltip,
        trigger: 'axis',
        axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(127,127,127,0.06)' } },
        formatter: (params: { dataIndex: number }[]) => {
          const id = ids[params[0]?.dataIndex ?? 0]
          const m = id ? metrics[id] : undefined
          if (!id || !m) return ''
          const rows = EXECUTION_OUTCOMES.map((o) =>
            tooltipRow(colors[o], OUTCOME_LABELS[o], `${formatNumber(m.execution[o])} · ${formatPercent(share(id, o), 0)}`),
          ).join('')
          return `<div style="margin-bottom:6px;color:${t.text2}">${names[id]} · ${formatNumber(m.plannedMoves)} planejadas</div>${rows}`
        },
      },
      xAxis: {
        type: 'value',
        max: 1,
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { color: t.text3, fontSize: 10.5, formatter: (v: number) => `${Math.round(v * 100)}%` },
      },
      yAxis: {
        type: 'category',
        data: ids.map((id) => names[id]),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: t.text2, fontSize: 11 },
      },
      series: EXECUTION_OUTCOMES.map((o, i) => ({
        name: OUTCOME_LABELS[o],
        type: 'bar',
        stack: 'share',
        barWidth: 14,
        data: ids.map((id) => share(id, o)),
        itemStyle: {
          color: colors[o],
          borderColor: t.surface,
          borderWidth: 1,
          borderRadius: i === 0 ? [4, 0, 0, 4] : i === EXECUTION_OUTCOMES.length - 1 ? [0, 4, 4, 0] : 0,
        },
      })),
    }
  }, [metrics, algorithms, names, theme])

  return <EChart option={option} height={height} ariaLabel="Barras 100% empilhadas do desfecho das recomendações por estratégia" />
}
