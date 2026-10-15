import { useMemo } from 'react'
import { formatKm, formatNumber } from '@/lib/format'
import type { ScenarioComparison } from '@/lib/metrics'
import { seriesHex } from '@/theme/colors'
import { useTheme } from '@/theme/ThemeProvider'
import { baseOption, CHART_TOKENS, valueAxis } from './chartTheme'
import { EChart } from './EChart'

/**
 * Cascata do efeito líquido: KM vazio do baseline → economia (ou perda) de pickup →
 * reposicionamento adicionado → KM vazio do cenário proposto.
 */
export function NetEffectChart({ comparison, name, height = 250 }: { comparison: ScenarioComparison; name: string; height?: number }) {
  const { theme } = useTheme()
  const option = useMemo(() => {
    const t = CHART_TOKENS[theme]
    const base = comparison.baseline.emptyKmTotal
    const saving = comparison.pickupSavingKm
    const afterPickup = base - saving
    const repos = comparison.repositionCostKm
    const final = comparison.proposed.emptyKmTotal
    const strategy = seriesHex(theme, comparison.algorithmId)
    const steps = [
      { label: 'Baseline', start: 0, end: base, color: seriesHex(theme, 'baseline'), text: formatKm(base, 0) },
      {
        label: saving >= 0 ? 'Pickup economizado' : 'Pickup adicional',
        start: Math.min(base, afterPickup),
        end: Math.max(base, afterPickup),
        color: t.neutralBar,
        text: `${saving >= 0 ? '−' : '+'}${formatNumber(Math.abs(saving))} km`,
      },
      {
        label: 'Reposicionamento',
        start: afterPickup,
        end: afterPickup + repos,
        color: strategy,
        text: `+${formatNumber(repos)} km`,
      },
      { label: name, start: 0, end: final, color: strategy, text: formatKm(final, 0) },
    ]
    return {
      ...baseOption(t),
      grid: { left: 8, right: 8, top: 22, bottom: 4, containLabel: true },
      tooltip: {
        ...baseOption(t).tooltip,
        trigger: 'item',
        formatter: (p: { dataIndex: number }) => {
          const s = steps[p.dataIndex]
          return s ? `<span style="color:${t.text2}">${s.label}</span><br/><b>${s.text}</b>` : ''
        },
      },
      xAxis: {
        type: 'category',
        data: steps.map((s) => s.label),
        axisLine: { lineStyle: { color: t.axis } },
        axisTick: { show: false },
        axisLabel: { color: t.text2, fontSize: 10.5, interval: 0, width: 92, overflow: 'break' },
      },
      yAxis: valueAxis(t, (v: number) => formatNumber(v)),
      series: [
        {
          type: 'bar',
          stack: 'w',
          silent: true,
          itemStyle: { color: 'transparent' },
          data: steps.map((s) => s.start),
          barWidth: 34,
        },
        {
          type: 'bar',
          stack: 'w',
          barWidth: 34,
          data: steps.map((s) => ({
            value: Math.max(0.0001, s.end - s.start),
            itemStyle: { color: s.color, borderRadius: 4 },
          })),
          label: {
            show: true,
            position: 'top',
            color: t.text1,
            fontSize: 11,
            fontWeight: 500,
            formatter: (p: { dataIndex: number }) => steps[p.dataIndex]?.text ?? '',
          },
        },
      ],
    }
  }, [comparison, name, theme])

  return (
    <EChart
      option={option}
      height={height}
      ariaLabel={`Cascata do KM vazio: baseline, variação de pickup, reposicionamento e ${name}`}
    />
  )
}
