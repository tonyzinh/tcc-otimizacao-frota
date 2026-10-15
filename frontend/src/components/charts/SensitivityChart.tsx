import { useMemo } from 'react'
import { formatPercent, formatSignedPercent } from '@/lib/format'
import { seriesHex } from '@/theme/colors'
import { useTheme } from '@/theme/ThemeProvider'
import type { AlgorithmId, ProposedAlgorithmId, SensitivityAnalysis } from '@/types'
import { baseOption, CHART_TOKENS, tooltipRow } from './chartTheme'
import { EChart } from './EChart'

/** Gráfico de pontos: redução do KM vazio por variação de parâmetro, uma série por estratégia. */
export function SensitivityChart({
  analysis,
  algorithms,
  names,
  height = 300,
}: {
  analysis: SensitivityAnalysis
  algorithms: readonly ProposedAlgorithmId[]
  names: Record<AlgorithmId, string>
  height?: number
}) {
  const { theme } = useTheme()
  const option = useMemo(() => {
    const t = CHART_TOKENS[theme]
    const variants = [...analysis.variants].reverse()
    const values = analysis.results.map((r) => r.reductionPercent ?? 0)
    const bound = Math.max(5, Math.ceil(Math.max(...values.map(Math.abs)) / 5) * 5)
    const find = (variantId: string, id: ProposedAlgorithmId) =>
      analysis.results.find((r) => r.variantId === variantId && r.algorithmId === id)
    return {
      ...baseOption(t),
      grid: { left: 8, right: 20, top: 34, bottom: 8, containLabel: true },
      tooltip: {
        ...baseOption(t).tooltip,
        trigger: 'axis',
        axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(127,127,127,0.06)' } },
        formatter: (params: { dataIndex: number }[]) => {
          const v = variants[params[0]?.dataIndex ?? 0]
          if (!v) return ''
          const rows = algorithms
            .map((id) => {
              const r = find(v.id, id)
              const cov = r ? ` · cob. ${formatPercent(r.proposedCoverage, 1)}` : ''
              return tooltipRow(seriesHex(theme, id), names[id], `${formatSignedPercent(r?.reductionPercent)}${cov}`)
            })
            .join('')
          return `<div style="margin-bottom:6px;color:${t.text2}">${v.label}</div>${rows}`
        },
      },
      xAxis: {
        type: 'value',
        min: -bound,
        max: bound,
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: t.grid } },
        axisLabel: { color: t.text3, fontSize: 10.5, formatter: (v: number) => `${v > 0 ? '+' : ''}${v}%` },
      },
      yAxis: {
        type: 'category',
        data: variants.map((v) => v.label),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: t.text2, fontSize: 11 },
        splitLine: { show: true, lineStyle: { color: t.grid, type: 'dashed' } },
      },
      series: algorithms.map((id, index) => ({
        name: names[id],
        type: 'scatter',
        symbolSize: 10,
        symbolOffset: [0, (index - (algorithms.length - 1) / 2) * 7],
        itemStyle: { color: seriesHex(theme, id), borderColor: t.surface, borderWidth: 1.5 },
        data: variants.map((v) => {
          const r = find(v.id, id)
          return r?.reductionPercent === null || r === undefined ? null : Math.round(r.reductionPercent * 10) / 10
        }),
        markLine:
          index === 0
            ? {
                silent: true,
                symbol: 'none',
                lineStyle: { color: t.zeroLine, type: 'solid', width: 1 },
                label: { show: true, formatter: 'sem efeito', color: t.text3, fontSize: 10, position: 'end' },
                data: [{ xAxis: 0 }],
              }
            : undefined,
      })),
    }
  }, [analysis, algorithms, names, theme])

  return <EChart option={option} height={height} ariaLabel="Gráfico de pontos da redução do KM vazio por variação de parâmetro" />
}
