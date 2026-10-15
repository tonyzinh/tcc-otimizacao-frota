import { BarChart, LineChart, ScatterChart } from 'echarts/charts'
import {
  AriaComponent,
  DatasetComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
} from 'echarts/components'
import * as echarts from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import { useEffect, useRef } from 'react'
import { cn } from '@/lib/cn'

echarts.use([
  BarChart,
  LineChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  MarkAreaComponent,
  DatasetComponent,
  AriaComponent,
  SVGRenderer,
])

export type EChartOption = echarts.EChartsCoreOption

/**
 * Wrapper mínimo do ECharts (tree-shaken, renderer SVG). Recebe uma opção pronta; o tema vem dos
 * construtores de opção, que leem os tokens do design system.
 */
export function EChart({
  option,
  ariaLabel,
  className,
  height = 240,
}: {
  option: EChartOption
  ariaLabel: string
  className?: string
  height?: number
}) {
  const ref = useRef<HTMLDivElement>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const chart = echarts.init(el, null, { renderer: 'svg' })
    chartRef.current = chart
    const observer = new ResizeObserver(() => chart.resize())
    observer.observe(el)
    return () => {
      observer.disconnect()
      chart.dispose()
      chartRef.current = null
    }
  }, [])

  useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: true, lazyUpdate: true })
  }, [option])

  return <div ref={ref} role="img" aria-label={ariaLabel} className={cn('w-full', className)} style={{ height }} />
}
