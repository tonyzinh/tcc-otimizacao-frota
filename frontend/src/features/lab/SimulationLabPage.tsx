import { PlayCircle, SlidersHorizontal } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useCallback, useMemo, useState } from 'react'
import { Link } from 'react-router'
import { MapLegend } from '@/components/maps'
import { countStates } from '@/components/maps/transforms'
import { frameAt, requestHistogram, type RequestDisplayState, type Trail } from '@/components/simulation/replayEngine'
import { Timeline } from '@/components/simulation/Timeline'
import { Button } from '@/components/ui/button'
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/feedback'
import { FloatingPanel } from '@/components/ui/panel'
import { Segmented } from '@/components/ui/segmented'
import { Select } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { AlgorithmSwatch } from '@/features/shared/AlgorithmTag'
import { DataKindBadge } from '@/features/shared/DataNotice'
import { useExperimentContext } from '@/features/shared/ExperimentContext'
import { VEHICLE_STATE_LABELS, VEHICLE_STATES } from '@/features/shared/labels'
import { layerItems } from '@/features/shared/layerCatalog'
import { FilterChips, LayerToggles } from '@/features/shared/LayerToggles'
import { MapFrame } from '@/features/shared/MapFrame'
import { MapTooltipContent } from '@/features/shared/MapTooltip'
import { buildLegend, useScenarioLayers, type ExecutionFilter, type LayerKey } from '@/features/shared/scenarioLayers'
import { selectionFromPick, type MapSelection } from '@/features/shared/selection'
import { useDaySnapshot, useReplayModel, useScenarioRun } from '@/features/shared/useStudyData'
import { cn } from '@/lib/cn'
import { formatClock, formatNumber } from '@/lib/format'
import { MINUTE } from '@/lib/time'
import { useTheme } from '@/theme/ThemeProvider'
import type { AlgorithmId, VehicleState } from '@/types'
import { DetailPanel } from './DetailPanel'

const LAB_LAYERS: LayerKey[] = ['basemap', 'demand', 'heat', 'requests', 'vehicles', 'planned', 'executed', 'trails', 'flows', 'concentration']
const ALL_REQUEST_STATES: ReadonlySet<RequestDisplayState> = new Set(['waiting', 'served', 'unserved'])
const TRAIL_KINDS: ReadonlySet<Trail['kind']> = new Set(['repositioning', 'to_pickup'])

export default function SimulationLabPage() {
  const { theme } = useTheme()
  const { experiment, date, algorithms, names } = useExperimentContext()
  const [algorithmId, setAlgorithmId] = useState<AlgorithmId>('guloso')
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>({
    basemap: true,
    demand: true,
    heat: false,
    requests: true,
    vehicles: true,
    planned: true,
    executed: true,
    trails: false,
    flows: false,
    concentration: false,
  })
  const [vehicleStates, setVehicleStates] = useState<ReadonlySet<VehicleState>>(
    () => new Set<VehicleState>(['idle', 'repositioning', 'to_pickup', 'on_trip']),
  )
  const [executionFilter, setExecutionFilter] = useState<ExecutionFilter>('all')
  const [minDemand, setMinDemand] = useState(0)
  const [selection, setSelection] = useState<MapSelection | null>(null)
  const [offset, setOffset] = useState(75 * MINUTE)
  const [panelOpen, setPanelOpen] = useState(true)
  // Em telas largas os painéis flutuam sobre o mapa: o enquadramento inicial desconta essa área.
  const [mapPadding] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia('(min-width: 768px)').matches
      ? { top: 24, bottom: 150, left: 300, right: 320 }
      : 16,
  )

  const snapshot = useDaySnapshot(experiment?.id, date)
  const run = useScenarioRun(experiment?.id, date, algorithmId)
  const baseline = useScenarioRun(experiment?.id, date, 'baseline')
  const model = useReplayModel(snapshot.data, run.data)
  const time = model ? Math.min(model.timelineEnd, model.windowStart + offset) : 0
  const frame = useMemo(() => (model ? frameAt(model, time) : null), [model, time])
  const histogram = useMemo(() => (model ? requestHistogram(model, 5 * MINUTE) : undefined), [model])
  const markers = useMemo(
    () =>
      (run.data?.movements ?? [])
        .filter((m) => m.executedStart)
        .map((m) => ({ t: Date.parse(m.executedStart!), tone: 'series' as const, color: `var(--series-${algorithmId === 'atribuicao_otima' ? 'atribuicao' : algorithmId})` })),
    [run.data, algorithmId],
  )
  const maxDemand = useMemo(() => Math.ceil(Math.max(1, ...(snapshot.data?.zones ?? []).map((z) => z.forecastRides))), [snapshot.data])
  const trails = useMemo(() => ({ accumulate: true, headSeconds: 600, kinds: TRAIL_KINDS }), [])

  const layerList = useScenarioLayers(
    snapshot.data && run.data && model && frame
      ? {
          idPrefix: '',
          theme,
          snapshot: snapshot.data,
          run: run.data,
          model,
          frame,
          layers,
          vehicleStates,
          requestStates: ALL_REQUEST_STATES,
          executionFilter,
          minDemand,
          selection,
          trails,
        }
      : null,
  )
  const legend = useMemo(() => buildLegend(theme, algorithmId, names[algorithmId], layers), [theme, algorithmId, names, layers])
  const counts = frame ? countStates(frame.vehicles) : null

  const onPick = useCallback((info: Parameters<typeof selectionFromPick>[0]) => setSelection(selectionFromPick(info)), [])
  const toggleState = (s: VehicleState) =>
    setVehicleStates((prev) => {
      const next = new Set(prev)
      if (next.has(s)) next.delete(s)
      else next.add(s)
      return next
    })

  const error = snapshot.error ?? run.error
  const ready = snapshot.data && run.data && model && frame && experiment

  return (
    <div className="flex h-full flex-col overflow-y-auto md:block md:overflow-hidden">
      <div className="relative h-[58vh] shrink-0 md:absolute md:inset-0 md:h-auto">
        {error ? (
          <div className="flex h-full items-center justify-center">
            <ErrorState error={error} />
          </div>
        ) : !ready ? (
          <Skeleton className="h-full w-full rounded-none opacity-50" />
        ) : (
          <MapFrame
            className="h-full w-full"
            ariaLabel="Mapa do Simulation Lab com camadas de demanda, veículos e reposicionamentos"
            layers={layerList}
            basemap={layers.basemap}
            padding={mapPadding}
            onPick={onPick}
            renderTooltip={(hover) => <MapTooltipContent hover={hover} />}
          />
        )}
      </div>

      {/* Coluna esquerda: camadas, filtros e legenda */}
      <div className="pointer-events-none z-10 order-3 flex flex-col gap-3 p-3 md:absolute md:top-3 md:bottom-3 md:left-3 md:w-[272px] md:p-0 xl:w-[288px]">
        <FloatingPanel className="pointer-events-auto flex min-h-0 flex-col">
          <div className="flex items-center gap-2 px-3 pt-3 pb-2">
            <Select<AlgorithmId>
              label="Estratégia exibida"
              value={algorithmId}
              onValueChange={(v) => {
                setAlgorithmId(v)
                setSelection(null)
              }}
              className="min-w-0 flex-1"
              options={(experiment?.algorithms ?? []).map((id) => ({
                value: id,
                label: names[id],
                leading: <AlgorithmSwatch id={id} />,
                hint: algorithms.find((a) => a.id === id)?.reference ?? undefined,
              }))}
            />
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={panelOpen ? 'Recolher camadas e filtros' : 'Expandir camadas e filtros'}
              aria-expanded={panelOpen}
              onClick={() => setPanelOpen((v) => !v)}
            >
              <SlidersHorizontal />
            </Button>
          </div>
          <AnimatePresence initial={false}>
            {panelOpen ? (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="flex min-h-0 flex-col overflow-hidden"
              >
                <div className="min-h-0 overflow-y-auto px-1.5 pb-2">
                  <div className="eyebrow px-2 pt-1 pb-1">Camadas</div>
                  <LayerToggles
                    items={layerItems(LAB_LAYERS)}
                    value={layers}
                    onChange={(k, v) => setLayers((prev) => ({ ...prev, [k]: v }))}
                  />
                  <div className="mt-2 grid gap-3 border-t border-line px-2 pt-3">
                    <div>
                      <div className="eyebrow mb-1.5">Estado do veículo</div>
                      <FilterChips
                        label="Estados de veículo visíveis"
                        options={VEHICLE_STATES.map((s) => ({ key: s, label: VEHICLE_STATE_LABELS[s] }))}
                        selected={vehicleStates}
                        onToggle={toggleState}
                      />
                    </div>
                    <div>
                      <div className="eyebrow mb-1.5">Recomendações</div>
                      <Segmented<ExecutionFilter>
                        label="Filtrar recomendações por desfecho"
                        size="sm"
                        value={executionFilter}
                        onValueChange={setExecutionFilter}
                        options={[
                          { value: 'all', label: 'Todas' },
                          { value: 'executed', label: 'Executadas' },
                          { value: 'not_executed', label: 'Não executadas' },
                        ]}
                      />
                    </div>
                    <div>
                      <div className="mb-1.5 flex items-center justify-between">
                        <span className="eyebrow">Demanda mínima por zona</span>
                        <span className="text-2xs text-fg-muted tabular">≥ {formatNumber(minDemand, 1)}</span>
                      </div>
                      <Slider
                        thumbLabel="Demanda prevista mínima por zona"
                        min={0}
                        max={maxDemand}
                        step={0.5}
                        value={[minDemand]}
                        onValueChange={(v) => setMinDemand(v[0] ?? 0)}
                        disabled={!layers.demand}
                      />
                    </div>
                  </div>
                </div>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </FloatingPanel>
        <MapLegend items={legend} className="pointer-events-auto hidden shrink-0 md:block" />
      </div>

      {/* Painel contextual de detalhes */}
      <div className="z-10 order-2 px-3 pb-3 md:absolute md:top-3 md:right-3 md:bottom-[156px] md:w-[288px] md:p-0 xl:bottom-3 xl:w-[300px]">
        <FloatingPanel className="max-h-full overflow-y-auto">
          {ready ? (
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={selection ? `${selection.kind}:${selection.id}` : 'summary'}
                initial={{ opacity: 0, x: 6 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -6 }}
                transition={{ duration: 0.16 }}
              >
                <DetailPanel
                  selection={selection}
                  onClose={() => setSelection(null)}
                  ctx={{
                    snapshot: snapshot.data!,
                    run: run.data!,
                    baseline: baseline.data?.metrics,
                    model: model!,
                    time,
                    algorithm: algorithms.find((a) => a.id === algorithmId),
                    algorithmName: names[algorithmId],
                  }}
                />
              </motion.div>
            </AnimatePresence>
          ) : (
            <EmptyState title="Carregando cenário" description="Preparando o dia selecionado." />
          )}
        </FloatingPanel>
      </div>

      {/* Linha do tempo */}
      {model && frame ? (
        <div className="z-10 order-1 px-3 pt-3 pb-3 md:absolute md:right-3 md:bottom-3 md:left-[296px] md:p-0 xl:right-[324px] xl:left-[312px]">
          <FloatingPanel className="px-4 pt-2.5 pb-2">
            <div className="mb-1 flex flex-wrap items-center gap-x-4 gap-y-1">
              <div className="flex items-baseline gap-2">
                <span className="font-mono text-[15px] font-medium text-fg tabular">{formatClock(time)}</span>
                <span className="text-2xs text-fg-subtle">horizonte D+1</span>
              </div>
              {counts ? (
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-2xs text-fg-muted tabular">
                  <span>{counts.idle} livres</span>
                  <span className={cn(counts.repositioning > 0 && 'text-fg')}>{counts.repositioning} reposicionando</span>
                  <span>{counts.to_pickup} em pickup</span>
                  <span>{counts.on_trip} em corrida</span>
                  <span className="text-fg-subtle">· {frame.cumulative.pending} aguardando</span>
                </div>
              ) : null}
              <DataKindBadge provenance={snapshot.data?.provenance} className="ml-auto" />
              <Button asChild variant="ghost" size="xs">
                <Link to="/replay">
                  <PlayCircle /> Replay
                </Link>
              </Button>
            </div>
            <Timeline
              start={model.windowStart}
              end={model.timelineEnd}
              windowEnd={model.windowEnd}
              value={time}
              onChange={(t) => setOffset(t - model.windowStart)}
              histogram={histogram}
              markers={markers}
              stepMs={MINUTE}
            />
          </FloatingPanel>
        </div>
      ) : null}

      {ready && run.data!.movements.length === 0 && algorithmId !== 'baseline' ? (
        <div className="pointer-events-none absolute inset-x-0 top-1/3 z-10 hidden justify-center md:flex">
          <FloatingPanel className="pointer-events-auto">
            <EmptyState title="Sem recomendações neste dia" description="O cenário não planejou reposicionamentos para o recorte selecionado." />
          </FloatingPanel>
        </div>
      ) : null}
    </div>
  )
}
