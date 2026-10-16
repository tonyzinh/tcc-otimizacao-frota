import { ArrowLeftRight, Link2, Unlink2 } from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'
import { createMapSync, MapLegend } from '@/components/maps'
import { topZoneShare, vehiclesByZone } from '@/components/maps/transforms'
import { frameAt, requestHistogram, type RequestDisplayState, type Trail } from '@/components/simulation/replayEngine'
import { Timeline } from '@/components/simulation/Timeline'
import { Button } from '@/components/ui/button'
import { ErrorState, Skeleton } from '@/components/ui/feedback'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Tooltip } from '@/components/ui/tooltip'
import { AlgorithmSwatch } from '@/features/shared/AlgorithmTag'
import { resolveAlgorithm, useExperimentContext } from '@/features/shared/ExperimentContext'
import { LAYER_ITEMS } from '@/features/shared/layerCatalog'
import { FilterChips } from '@/features/shared/LayerToggles'
import { MapFrame } from '@/features/shared/MapFrame'
import { MapTooltipContent } from '@/features/shared/MapTooltip'
import { buildLegend, useScenarioLayers, type LayerKey } from '@/features/shared/scenarioLayers'
import { useDaySnapshot, useReplayModel, useScenarioRun } from '@/features/shared/useStudyData'
import { cn } from '@/lib/cn'
import { formatClock, formatSignedKm, formatSignedPercent, formatSignedPoints } from '@/lib/format'
import { compareScenario } from '@/lib/metrics'
import { MINUTE } from '@/lib/time'
import { useTheme } from '@/theme/ThemeProvider'
import type { AlgorithmId, VehicleState } from '@/types'
import { ScenarioOverlay } from './ScenarioOverlay'

const TOGGLEABLE: LayerKey[] = ['basemap', 'demand', 'vehicles', 'requests', 'planned', 'executed', 'trails', 'flows']
const VEHICLE_STATES: ReadonlySet<VehicleState> = new Set(['idle', 'repositioning', 'to_pickup', 'on_trip'])
const REQUEST_STATES: ReadonlySet<RequestDisplayState> = new Set(['waiting', 'unserved'])
const TRAILS = { accumulate: true, headSeconds: 600, kinds: new Set<Trail['kind']>(['repositioning', 'to_pickup']) }

export default function ComparisonPage() {
  const { theme } = useTheme()
  const { experiment, date, names } = useExperimentContext()
  const available = experiment?.algorithms ?? []
  const [pickA, setA] = useState<AlgorithmId>('guloso')
  const [pickB, setB] = useState<AlgorithmId>('atribuicao_otima')
  const a = resolveAlgorithm(available, pickA)
  const b = resolveAlgorithm(available, pickB, a)
  const [syncOn, setSyncOn] = useState(true)
  const [offset, setOffset] = useState(90 * MINUTE)
  const [enabled, setEnabled] = useState<ReadonlySet<LayerKey>>(
    () => new Set<LayerKey>(['basemap', 'demand', 'vehicles', 'requests', 'planned', 'executed']),
  )
  const sync = useMemo(() => createMapSync(), [])

  const snapshot = useDaySnapshot(experiment?.id, date)
  const runA = useScenarioRun(experiment?.id, date, a)
  const runB = useScenarioRun(experiment?.id, date, b)
  const baseline = useScenarioRun(experiment?.id, date, 'baseline')
  const modelA = useReplayModel(snapshot.data, runA.data)
  const modelB = useReplayModel(snapshot.data, runB.data)
  const end = Math.max(modelA?.timelineEnd ?? 0, modelB?.timelineEnd ?? 0)
  const start = modelA?.windowStart ?? modelB?.windowStart ?? 0
  const time = Math.min(end, start + offset)
  const frameA = useMemo(() => (modelA ? frameAt(modelA, time) : null), [modelA, time])
  const frameB = useMemo(() => (modelB ? frameAt(modelB, time) : null), [modelB, time])
  const histogram = useMemo(() => (modelA ? requestHistogram(modelA, 5 * MINUTE) : undefined), [modelA])

  const layers = useMemo(() => {
    const out = {} as Record<LayerKey, boolean>
    for (const k of Object.keys(LAYER_ITEMS) as LayerKey[]) out[k] = enabled.has(k)
    return out
  }, [enabled])

  const common = snapshot.data
    ? {
        theme,
        snapshot: snapshot.data,
        layers,
        vehicleStates: VEHICLE_STATES,
        requestStates: REQUEST_STATES,
        executionFilter: 'all' as const,
        minDemand: 0,
        selection: null,
        trails: TRAILS,
      }
    : null
  const layersA = useScenarioLayers(common && runA.data && modelA && frameA ? { ...common, idPrefix: 'a-', run: runA.data, model: modelA, frame: frameA } : null)
  const layersB = useScenarioLayers(common && runB.data && modelB && frameB ? { ...common, idPrefix: 'b-', run: runB.data, model: modelB, frame: frameB } : null)

  const toggleLayer = useCallback((k: LayerKey) => {
    setEnabled((prev) => {
      const next = new Set(prev)
      if (next.has(k)) next.delete(k)
      else next.add(k)
      return next
    })
  }, [])

  const options = (experiment?.algorithms ?? []).map((id) => ({ value: id, label: names[id], leading: <AlgorithmSwatch id={id} /> }))
  const metricsA = runA.data?.metrics
  const metricsB = runB.data?.metrics
  const diff = metricsA && metricsB ? compareScenario(metricsA, metricsB) : null
  const vsBaseline = (m: typeof metricsA) => (m && baseline.data ? compareScenario(baseline.data.metrics, m) : null)
  const error = snapshot.error ?? runA.error ?? runB.error
  const legend = buildLegend(theme, a, names[a], layers).filter((i) => !i.id.startsWith('v-') || i.id === 'v-repo')

  const mapPane = (side: 'A' | 'B') => {
    const id = side === 'A' ? a : b
    const run = side === 'A' ? runA.data : runB.data
    const frame = side === 'A' ? frameA : frameB
    const list = side === 'A' ? layersA : layersB
    const cmp = vsBaseline(run?.metrics)
    return (
      <div className="relative h-[46vh] min-h-[320px] md:h-auto md:min-h-0">
        {run && frame ? (
          <MapFrame
            className="absolute inset-0"
            ariaLabel={`Mapa do cenário ${side}: ${names[id]}`}
            layers={list}
            basemap={layers.basemap}
            sync={syncOn ? sync : undefined}
            showNavigation={side === 'B'}
            renderTooltip={(hover) => <MapTooltipContent hover={hover} />}
          />
        ) : (
          <Skeleton className="absolute inset-0 rounded-none opacity-50" />
        )}
        {run && frame ? (
          <div className="pointer-events-none absolute inset-x-3 top-3 z-10 flex flex-col items-start gap-2">
            <ScenarioOverlay
              className="pointer-events-auto w-full max-w-[400px]"
              algorithmId={id}
              name={names[id]}
              metrics={run.metrics}
              counters={frame.cumulative}
              concentration={topZoneShare(vehiclesByZone(frame.vehicles, experiment?.h3Resolution ?? 7), 5)}
            />
            {cmp ? (
              <span
                className={cn(
                  'glass pointer-events-auto rounded-md border border-line px-2 py-1 text-2xs tabular',
                  (cmp.reductionPercent ?? 0) > 0 ? 'text-success-text' : 'text-critical-text',
                )}
              >
                {formatSignedPercent(cmp.reductionPercent)} KM vazio vs baseline · cobertura {formatSignedPoints(cmp.coverageDelta)}
              </span>
            ) : null}
          </div>
        ) : null}
        <span className="pointer-events-none absolute bottom-3 left-3 z-10 rounded-md bg-overlay px-1.5 py-0.5 font-mono text-[10px] text-fg-subtle">
          {side}
        </span>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto md:overflow-hidden">
      <div className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2 border-b border-line bg-surface px-3 py-2 md:px-4">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[10px] text-fg-subtle">A</span>
          <Select<AlgorithmId> label="Estratégia A" size="sm" value={a} onValueChange={setA} options={options} triggerClassName="w-[172px]" />
          <Tooltip content="Trocar A e B">
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Trocar estratégias A e B"
              onClick={() => {
                setA(b)
                setB(a)
              }}
            >
              <ArrowLeftRight />
            </Button>
          </Tooltip>
          <span className="font-mono text-[10px] text-fg-subtle">B</span>
          <Select<AlgorithmId> label="Estratégia B" size="sm" value={b} onValueChange={setB} options={options} triggerClassName="w-[172px]" />
        </div>
        <FilterChips
          label="Camadas visíveis nos dois mapas"
          options={TOGGLEABLE.map((k) => ({ key: k, label: LAYER_ITEMS[k].label.replace('Reposicionamento ', '') }))}
          selected={enabled}
          onToggle={toggleLayer}
        />
        <label className="ml-auto flex cursor-pointer items-center gap-2 text-xs text-fg-muted">
          {syncOn ? <Link2 className="size-3.5" aria-hidden /> : <Unlink2 className="size-3.5" aria-hidden />}
          Câmera sincronizada
          <Switch checked={syncOn} onCheckedChange={setSyncOn} aria-label="Sincronizar câmera dos mapas" />
        </label>
      </div>

      {error ? (
        <div className="flex flex-1 items-center justify-center">
          <ErrorState error={error} />
        </div>
      ) : (
        <div className="grid shrink-0 gap-px bg-line md:min-h-0 md:flex-1 md:shrink md:grid-cols-2">
          {mapPane('A')}
          {mapPane('B')}
        </div>
      )}

      <div className="grid shrink-0 gap-x-6 gap-y-3 border-t border-line bg-surface px-3 py-3 md:px-4 lg:grid-cols-[minmax(0,1fr)_auto]">
        {modelA ? (
          <div className="min-w-0">
            <div className="mb-1 flex items-baseline gap-2">
              <span className="font-mono text-[15px] font-medium text-fg tabular">{formatClock(time)}</span>
              <span className="text-2xs text-fg-subtle">mesmo dia, horário, zoom e posição nos dois mapas</span>
            </div>
            <Timeline
              start={start}
              end={end}
              windowEnd={modelA.windowEnd}
              value={time}
              onChange={(t) => setOffset(t - start)}
              histogram={histogram}
              stepMs={MINUTE}
            />
          </div>
        ) : (
          <Skeleton className="h-16" />
        )}
        <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
          {diff ? (
            <dl className="grid grid-cols-3 gap-x-5 gap-y-0.5 text-xs">
              <dt className="col-span-3 eyebrow mb-1">B em relação a A · dia inteiro</dt>
              <div>
                <dd className={cn('font-semibold tabular', diff.netKm >= 0 ? 'text-success-text' : 'text-critical-text')}>
                  {formatSignedKm(-diff.netKm, 0)}
                </dd>
                <dt className="text-[10px] text-fg-subtle">KM vazio</dt>
              </div>
              <div>
                <dd className="font-medium text-fg tabular">{formatSignedKm(-diff.pickupSavingKm, 0)}</dd>
                <dt className="text-[10px] text-fg-subtle">pickup</dt>
              </div>
              <div>
                <dd className={cn('font-medium tabular', (diff.coverageDelta ?? 0) >= 0 ? 'text-fg' : 'text-critical-text')}>
                  {formatSignedPoints(diff.coverageDelta)}
                </dd>
                <dt className="text-[10px] text-fg-subtle">cobertura</dt>
              </div>
            </dl>
          ) : null}
          <MapLegend items={legend} collapsible={false} className="hidden max-w-[300px] border-none bg-transparent p-0 shadow-none backdrop-blur-none xl:block [&_ul]:grid-cols-2 [&_ul]:gap-x-3" />
        </div>
      </div>
    </div>
  )
}
