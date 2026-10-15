import { useCallback, useMemo, useState } from 'react'
import { createMapSync, MapLegend } from '@/components/maps'
import { CumulativeKmChart, type CumulativeSeries } from '@/components/charts/CumulativeKmChart'
import {
  cumulativeSeries,
  frameAt,
  nextEventTime,
  previousEventTime,
  requestHistogram,
  type ReplayModel,
  type RequestDisplayState,
  type Trail,
} from '@/components/simulation/replayEngine'
import { ReplayControls } from '@/components/simulation/ReplayControls'
import { Timeline, type TimelineMarker } from '@/components/simulation/Timeline'
import { useReplayClock } from '@/components/simulation/useReplayClock'
import { ErrorState, Skeleton } from '@/components/ui/feedback'
import { FloatingPanel } from '@/components/ui/panel'
import { Segmented } from '@/components/ui/segmented'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { AlgorithmSwatch, AlgorithmTag } from '@/features/shared/AlgorithmTag'
import { DataKindBadge } from '@/features/shared/DataNotice'
import { useExperimentContext } from '@/features/shared/ExperimentContext'
import { FilterChips } from '@/features/shared/LayerToggles'
import { MapFrame } from '@/features/shared/MapFrame'
import { MapTooltipContent } from '@/features/shared/MapTooltip'
import { buildLegend, useScenarioLayers, type LayerKey } from '@/features/shared/scenarioLayers'
import { useDaySnapshot, useReplayModel, useScenarioRun } from '@/features/shared/useStudyData'
import { cn } from '@/lib/cn'
import { formatKm, formatNumber } from '@/lib/format'
import { MINUTE } from '@/lib/time'
import { seriesHex } from '@/theme/colors'
import { useTheme } from '@/theme/ThemeProvider'
import type { AlgorithmId, CumulativeCounters, ScenarioRun, VehicleState } from '@/types'
import { EventLog } from './EventLog'

const VEHICLE_STATES: ReadonlySet<VehicleState> = new Set(['idle', 'repositioning', 'to_pickup', 'on_trip'])
const REQUEST_STATES: ReadonlySet<RequestDisplayState> = new Set(['waiting', 'unserved'])
type TrailLength = '300' | '900' | '2700'

function Counters({ id, name, c }: { id: AlgorithmId; name: string; c: CumulativeCounters }) {
  return (
    <div className="grid gap-1.5">
      <AlgorithmTag id={id} name={name} className="text-xs font-medium text-fg" />
      <dl className="grid grid-cols-3 gap-x-3 gap-y-1.5 text-xs tabular">
        {[
          ['Pickup', formatKm(c.pickupKm, 1)],
          ['Reposic.', formatKm(c.repositionKm, 1)],
          ['KM vazio', formatKm(c.emptyKm, 1)],
          ['Atendidas', formatNumber(c.served)],
          ['Aguardando', formatNumber(c.pending)],
          ['Não atend.', formatNumber(c.unserved)],
        ].map(([label, value], i) => (
          <div key={label}>
            <dt className="text-[10px] text-fg-subtle">{label}</dt>
            <dd className={cn(i === 2 ? 'font-semibold text-fg' : 'text-fg-muted')}>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

function lastEventIndex(run: ScenarioRun | undefined, times: number[] | null, t: number): number {
  if (!run || !times) return 0
  let lo = 0
  let hi = times.length
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (times[mid]! <= t) lo = mid + 1
    else hi = mid
  }
  return lo
}

export default function ReplayPage() {
  const { theme } = useTheme()
  const { experiment, date, names, shortNames } = useExperimentContext()
  const [a, setA] = useState<AlgorithmId>('guloso')
  const [compare, setCompare] = useState(false)
  const [b, setB] = useState<AlgorithmId>('baseline')
  const [accumulate, setAccumulate] = useState(true)
  const [trailLength, setTrailLength] = useState<TrailLength>('900')
  const [trailKinds, setTrailKinds] = useState<ReadonlySet<Trail['kind']>>(() => new Set<Trail['kind']>(['repositioning', 'to_pickup']))
  const [show, setShow] = useState({ requests: true, demand: false, planned: true, basemap: true })
  const sync = useMemo(() => createMapSync(), [])

  const snapshot = useDaySnapshot(experiment?.id, date)
  const runA = useScenarioRun(experiment?.id, date, a)
  const runB = useScenarioRun(experiment?.id, date, b)
  const baseline = useScenarioRun(experiment?.id, date, 'baseline')
  const modelA = useReplayModel(snapshot.data, runA.data)
  const modelB = useReplayModel(snapshot.data, runB.data)
  const modelBase = useReplayModel(snapshot.data, baseline.data)

  const start = modelA?.windowStart ?? 0
  const end = Math.max(modelA?.timelineEnd ?? 0, compare ? (modelB?.timelineEnd ?? 0) : 0)
  const clock = useReplayClock(start, end, start)
  const time = clock.time

  const frameA = useMemo(() => (modelA ? frameAt(modelA, time) : null), [modelA, time])
  const frameB = useMemo(() => (modelB && compare ? frameAt(modelB, time) : null), [modelB, compare, time])

  const layers = useMemo<Record<LayerKey, boolean>>(
    () => ({
      basemap: show.basemap,
      demand: show.demand,
      heat: false,
      requests: show.requests,
      vehicles: true,
      planned: show.planned,
      executed: false,
      trails: true,
      flows: false,
      concentration: false,
    }),
    [show],
  )
  const trails = useMemo(
    () => ({ accumulate, headSeconds: Number(trailLength), kinds: trailKinds }),
    [accumulate, trailLength, trailKinds],
  )
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
        trails,
      }
    : null
  const layersA = useScenarioLayers(common && runA.data && modelA && frameA ? { ...common, idPrefix: 'a-', run: runA.data, model: modelA, frame: frameA } : null)
  const layersB = useScenarioLayers(common && runB.data && modelB && frameB ? { ...common, idPrefix: 'b-', run: runB.data, model: modelB, frame: frameB } : null)

  const onPrev = useCallback(() => modelA && clock.seek(previousEventTime(modelA, clock.time)), [modelA, clock])
  const onNext = useCallback(() => modelA && clock.seek(nextEventTime(modelA, clock.time)), [modelA, clock])

  const histogram = useMemo(() => (modelA ? requestHistogram(modelA, 5 * MINUTE) : undefined), [modelA])
  const markers = useMemo<TimelineMarker[]>(
    () =>
      (runA.data?.movements ?? [])
        .filter((m) => m.executedStart)
        .map((m) => ({ t: Date.parse(m.executedStart!), tone: 'series', color: seriesHex(theme, a) })),
    [runA.data, theme, a],
  )
  const eventTimesA = useMemo(() => runA.data?.events.map((e) => Date.parse(e.t)) ?? null, [runA.data])
  const eventIndex = lastEventIndex(runA.data, eventTimesA, time)

  const seriesFor = useCallback(
    (id: AlgorithmId, model: ReplayModel | null): CumulativeSeries | null =>
      model ? { algorithmId: id, name: shortNames[id], points: cumulativeSeries(model, 2 * MINUTE).map((p) => ({ t: p.t, emptyKm: p.emptyKm })) } : null,
    [shortNames],
  )
  const chartSeries = useMemo(() => {
    const list: CumulativeSeries[] = []
    const sa = seriesFor(a, modelA)
    if (sa) list.push(sa)
    if (compare && b !== a) {
      const sb = seriesFor(b, modelB)
      if (sb) list.push(sb)
    }
    if (a !== 'baseline' && (!compare || b !== 'baseline')) {
      const base = seriesFor('baseline', modelBase)
      if (base) list.push(base)
    }
    return list
  }, [seriesFor, a, b, compare, modelA, modelB, modelBase])

  const options = (experiment?.algorithms ?? []).map((id) => ({ value: id, label: names[id], leading: <AlgorithmSwatch id={id} /> }))
  const legend = buildLegend(theme, a, names[a], layers).filter((i) => !['v-idle', 'v-trip'].includes(i.id))
  const error = snapshot.error ?? runA.error ?? runB.error

  const mapPane = (side: 'A' | 'B') => {
    const id = side === 'A' ? a : b
    const frame = side === 'A' ? frameA : frameB
    const list = side === 'A' ? layersA : layersB
    return (
      <div className="relative h-[48vh] min-h-[300px] md:h-auto md:min-h-0">
        {frame ? (
          <MapFrame
            className="absolute inset-0"
            ariaLabel={`Replay do cenário ${names[id]}`}
            layers={list}
            basemap={show.basemap}
            sync={compare ? sync : undefined}
            showNavigation={side === (compare ? 'B' : 'A')}
            renderTooltip={(hover) => <MapTooltipContent hover={hover} />}
          />
        ) : (
          <Skeleton className="absolute inset-0 rounded-none opacity-50" />
        )}
        {frame ? (
          <FloatingPanel className="absolute top-3 left-3 z-10 px-3 py-2">
            <div className="flex items-center gap-3">
              <AlgorithmTag id={id} name={names[id]} className="text-xs font-medium text-fg" />
              <span className="text-xs text-fg-muted tabular">{formatKm(frame.cumulative.emptyKm, 1)} vazio</span>
            </div>
          </FloatingPanel>
        ) : null}
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto md:flex-row md:overflow-hidden">
      <section className="flex min-w-0 shrink-0 flex-col md:min-h-0 md:flex-1 md:shrink">
        {error ? (
          <div className="flex flex-1 items-center justify-center">
            <ErrorState error={error} />
          </div>
        ) : (
          <div className={cn('relative grid gap-px bg-line md:min-h-0 md:flex-1', compare && 'md:grid-cols-2')}>
            {mapPane('A')}
            {compare ? mapPane('B') : null}
            <MapLegend items={legend} defaultOpen={false} className="absolute bottom-3 left-3 z-10 hidden w-[220px] md:block" />
          </div>
        )}
        <div className="shrink-0 border-t border-line bg-surface px-3 pt-2.5 pb-3 md:px-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <ReplayControls clock={clock} onPreviousEvent={onPrev} onNextEvent={onNext} />
            <DataKindBadge provenance={snapshot.data?.provenance} />
          </div>
          {modelA ? (
            <Timeline
              start={start}
              end={end}
              windowEnd={modelA.windowEnd}
              value={time}
              onChange={clock.seek}
              histogram={histogram}
              markers={markers}
              stepMs={15_000}
            />
          ) : (
            <Skeleton className="h-14" />
          )}
        </div>
      </section>

      <aside className="w-full shrink-0 border-t border-line bg-surface md:w-[320px] md:overflow-y-auto md:border-t-0 md:border-l">
        <div className="grid gap-3 border-b border-line p-4">
          <div>
            <div className="eyebrow mb-1.5">Estratégia</div>
            <Select<AlgorithmId> label="Estratégia reproduzida" value={a} onValueChange={setA} options={options} className="w-full" />
          </div>
          <label className="flex cursor-pointer items-center justify-between gap-3 text-xs text-fg">
            Comparar no mesmo instante
            <Switch checked={compare} onCheckedChange={setCompare} aria-label="Comparar com outra estratégia" />
          </label>
          {compare ? (
            <Select<AlgorithmId> label="Estratégia de comparação" value={b} onValueChange={setB} options={options} className="w-full" />
          ) : null}
        </div>

        <div className="grid gap-3 border-b border-line p-4">
          <div className="eyebrow">Rastros</div>
          <label className="flex cursor-pointer items-center justify-between gap-3 text-xs text-fg">
            Acumular rastros (esmaecem com o tempo)
            <Switch checked={accumulate} onCheckedChange={setAccumulate} aria-label="Acumular rastros" />
          </label>
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs text-fg-muted">Cauda ativa</span>
            <Segmented<TrailLength>
              label="Comprimento da cauda ativa"
              size="sm"
              value={trailLength}
              onValueChange={setTrailLength}
              options={[
                { value: '300', label: '5 min' },
                { value: '900', label: '15 min' },
                { value: '2700', label: '45 min' },
              ]}
            />
          </div>
          <FilterChips
            label="Tipos de rastro"
            options={[
              { key: 'repositioning', label: 'Reposicionamento' },
              { key: 'to_pickup', label: 'Pickup' },
              { key: 'on_trip', label: 'Com passageiro' },
            ]}
            selected={trailKinds}
            onToggle={(k) =>
              setTrailKinds((prev) => {
                const next = new Set(prev)
                if (next.has(k)) next.delete(k)
                else next.add(k)
                return next
              })
            }
          />
          <div className="grid gap-2">
            {(
              [
                ['requests', 'Solicitações aguardando e não atendidas'],
                ['planned', 'Plano preventivo (tracejado)'],
                ['demand', 'Demanda prevista (H3)'],
                ['basemap', 'Base cartográfica'],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="flex cursor-pointer items-center justify-between gap-3 text-xs text-fg-muted">
                {label}
                <Switch checked={show[key]} onCheckedChange={(v) => setShow((s) => ({ ...s, [key]: v }))} aria-label={label} />
              </label>
            ))}
          </div>
        </div>

        <div className="grid gap-3 border-b border-line p-4">
          <div className="eyebrow">Acumulado até o instante</div>
          {frameA ? <Counters id={a} name={names[a]} c={frameA.cumulative} /> : <Skeleton className="h-16" />}
          {compare && frameB ? <Counters id={b} name={names[b]} c={frameB.cumulative} /> : null}
          {chartSeries.length > 0 ? <CumulativeKmChart series={chartSeries} playhead={time} /> : null}
        </div>

        <div className="pt-3">
          <div className="eyebrow px-4 pb-1.5">Eventos recentes · {names[a]}</div>
          {runA.data && snapshot.data ? <EventLog run={runA.data} snapshot={snapshot.data} upToIndex={eventIndex} /> : null}
          <p className="border-t border-line px-4 py-3 text-[11px] text-fg-subtle">
            Reprodução de eventos simulados a partir de dados fictícios. Não representa despacho em tempo real nem conexão operacional.
          </p>
        </div>
      </aside>
    </div>
  )
}
