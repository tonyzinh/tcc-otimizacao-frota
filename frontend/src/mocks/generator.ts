/**
 * Gerador demonstrativo do FleetLab.
 *
 * IMPORTANTE — leia antes de usar estes dados:
 * - Tudo aqui é FICTÍCIO e determinístico (semente fixa). Nada vem de `data/`, da Gold ou do
 *   Elasticsearch, e nenhum valor deve ser citado como resultado do TCC.
 * - Os planos de reposicionamento NÃO executam o guloso (DT001), o proporcional nem a atribuição
 *   ótima. São movimentos ilustrativos produzidos por uma rotina genérica com "perfis" arbitrários
 *   (`DEMO_PLAN_PROFILES`), apenas para que cada estratégia tenha um desenho visual distinto.
 * - O roteiro de eventos imita apenas o desenho público do replay (corte D+1, mesmo mundo para
 *   todos os cenários, veículo livre mais próximo, reposicionamento contado no KM vazio). Não é o
 *   simulador Python e não substitui `tcc-frota gold-replay`.
 */
import { cellToLatLng, gridDisk, latLngToCell } from 'h3-js'
import { haversineKm, illustrativeCurve } from '@/lib/geo'
import { emptyExecution, reductionPercent } from '@/lib/metrics'
import { createRng, hashString, normal, pickWeighted, poisson, uniform, type Rng } from '@/lib/random'
import { addDays, HOUR, localEpoch, MINUTE, toEpoch, toIso } from '@/lib/time'
import type {
  AlgorithmId,
  DaySnapshot,
  DayResult,
  DemandZone,
  ExecutionOutcome,
  Experiment,
  ExperimentParameters,
  ExperimentResults,
  FleetPosition,
  LngLat,
  ProposedAlgorithmId,
  RepositionMovement,
  RideRequest,
  ScenarioMetrics,
  ScenarioRun,
  SensitivityAnalysis,
  SensitivityResult,
  SensitivityVariant,
  SimulationEvent,
  Vehicle,
  VehicleState,
} from '@/types'
import { isOnLand, jitterOnLand, LOCALITIES, type Locality } from './geography'

const FLEET_SIZE = 58
const WEEKDAY_RIDES: Record<'morning' | 'evening', number> = { morning: 118, evening: 128 }
const BOARDING_MINUTES = 1

/** Perfis arbitrários de demonstração — NÃO são parâmetros dos algoritmos do TCC. */
export const DEMO_PLAN_PROFILES: Record<ProposedAlgorithmId, { moveFraction: number; focus: number; distanceScaleKm: number }> = {
  guloso: { moveFraction: 0.22, focus: 1.6, distanceScaleKm: 2.5 },
  proporcional: { moveFraction: 0.18, focus: 1.0, distanceScaleKm: 3 },
  atribuicao_otima: { moveFraction: 0.16, focus: 1.2, distanceScaleKm: 2 },
}

type WindowKind = 'morning' | 'evening'

interface ZoneSeed {
  h3: string
  centroid: LngLat
  locality: Locality
  weight: number
}

interface VehicleProfile {
  vehicle: Vehicle
  presenceRate: number
  typical: LngLat
}

interface VehicleDay {
  vehicleId: string
  present: boolean
  start: LngLat
  availableFrom: number
  availableUntil: number
  commitment: boolean
}

export interface DemoWorld {
  experiment: Experiment
  snapshot: DaySnapshot
  windowStart: number
  windowEnd: number
  cutoff: number
  profiles: VehicleProfile[]
  vehicleDays: Map<string, VehicleDay>
}

interface PlannedMove {
  vehicleId: string
  from: LngLat
  fromZone: string
  toZone: string
  to: LngLat
}

const windowKind = (params: ExperimentParameters): WindowKind => (params.planHour >= 12 ? 'evening' : 'morning')

function originWeight(loc: Locality, kind: WindowKind): number {
  return kind === 'morning' ? loc.morningOrigin : loc.morningDestination
}

function destinationWeight(loc: Locality, kind: WindowKind): number {
  return kind === 'morning' ? loc.morningDestination : loc.morningOrigin
}

function cellOf(point: LngLat, resolution: number): string {
  return latLngToCell(point[1], point[0], resolution)
}

function shortHash(value: string): string {
  return hashString(value).toString(16).padStart(8, '0')
}

// ---------------------------------------------------------------------------------------------
// Zonas e frota (fixas por experimento)
// ---------------------------------------------------------------------------------------------

const zoneCache = new Map<string, ZoneSeed[]>()

export function buildZoneSeeds(experiment: Experiment): ZoneSeed[] {
  const cached = zoneCache.get(experiment.id)
  if (cached) return cached
  const kind = windowKind(experiment.parameters)
  const res = experiment.h3Resolution
  const cells = new Set<string>()
  for (const loc of LOCALITIES) {
    for (const cell of gridDisk(cellOf(loc.center, res), 2)) cells.add(cell)
  }
  const seeds: ZoneSeed[] = []
  for (const h3 of [...cells].sort()) {
    const [lat, lng] = cellToLatLng(h3)
    const centroid: LngLat = [lng, lat]
    if (!isOnLand(centroid)) continue
    let nearest = LOCALITIES[0]!
    let nearestKm = Infinity
    let weight = 0
    for (const loc of LOCALITIES) {
      const d = haversineKm(centroid, loc.center)
      if (d < nearestKm) {
        nearestKm = d
        nearest = loc
      }
      const sigma = loc.spreadKm * 1.3
      weight += originWeight(loc, kind) * Math.exp(-0.5 * (d / sigma) ** 2)
    }
    if (weight < 0.015) continue
    seeds.push({ h3, centroid, locality: nearest, weight })
  }
  zoneCache.set(experiment.id, seeds)
  return seeds
}

const fleetCache = new Map<string, VehicleProfile[]>()

export function buildFleetProfiles(experiment: Experiment): VehicleProfile[] {
  const cached = fleetCache.get(experiment.id)
  if (cached) return cached
  const rng = createRng(`${experiment.id}:fleet`)
  const profiles: VehicleProfile[] = []
  for (let i = 1; i <= FLEET_SIZE; i += 1) {
    const id = `V-${String(i).padStart(2, '0')}`
    const home = pickWeighted(rng, LOCALITIES, (l) => l.fleetHome)
    profiles.push({
      vehicle: { id, label: `Veículo demo ${String(i).padStart(2, '0')}` },
      presenceRate: uniform(rng, 0.38, 0.97),
      typical: jitterOnLand(rng, home.center, home.spreadKm),
    })
  }
  fleetCache.set(experiment.id, profiles)
  return profiles
}

function predictedFleet(world: DemoWorld, params: ExperimentParameters): FleetPosition[] {
  const res = world.experiment.h3Resolution
  return world.profiles
    .filter((p) => p.presenceRate >= params.minPresenceRate)
    .map((p) => ({
      vehicleId: p.vehicle.id,
      position: p.typical,
      zone: cellOf(p.typical, res),
      basis: 'predicted' as const,
      availableFrom: toIso(world.windowStart),
      availableUntil: toIso(world.windowEnd),
      state: 'idle' as const,
    }))
}

// ---------------------------------------------------------------------------------------------
// Mundo de D+1 (igual para todos os cenários)
// ---------------------------------------------------------------------------------------------

function dayFactor(date: string): number {
  const weekday = new Date(`${date}T12:00:00Z`).getUTCDay()
  if (weekday === 6) return 0.72
  if (weekday === 0) return 0.58
  return 1
}

function sampleMinute(rng: Rng, kind: WindowKind, horizonMinutes: number): number {
  const peak = kind === 'morning' ? 60 : 95
  if (rng() < 0.75) {
    // Reamostra fora da janela em vez de truncar, para não criar picos artificiais nas bordas.
    for (let attempt = 0; attempt < 8; attempt += 1) {
      const raw = normal(rng, peak, 38)
      if (raw >= 0 && raw < horizonMinutes) return raw
    }
  }
  return uniform(rng, 0, horizonMinutes)
}

const worldCache = new Map<string, DemoWorld>()

export function buildDayWorld(experiment: Experiment, date: string): DemoWorld {
  const key = `${experiment.id}|${date}`
  const cached = worldCache.get(key)
  if (cached) return cached

  const params = experiment.parameters
  const kind = windowKind(params)
  const res = experiment.h3Resolution
  const rng = createRng(`${experiment.id}:${date}:world`)
  const forecastRng = createRng(`${experiment.id}:${date}:forecast`)
  const windowStart = localEpoch(date, params.planHour * 60)
  const windowEnd = windowStart + params.horizonHours * HOUR
  const cutoff = localEpoch(addDays(date, -1), params.cutoffHour * 60)
  const horizonMinutes = params.horizonHours * 60

  const seeds = buildZoneSeeds(experiment)
  const totalWeight = seeds.reduce((s, z) => s + z.weight, 0)
  const factor = dayFactor(date)
  const shock = Math.max(0.75, normal(rng, 1, 0.09))
  const expectedTotal = WEEKDAY_RIDES[kind] * factor

  // Pedidos observados em D+1.
  const requests: RideRequest[] = []
  const observedByZone = new Map<string, number>()
  const forecastByZone = new Map<string, number>()
  const tag = date.slice(5).replace('-', '')
  for (const zone of seeds) {
    const expected = (expectedTotal * zone.weight) / totalWeight
    // Previsão: média histórica fictícia do mesmo dia da semana, sem acesso ao observado.
    forecastByZone.set(zone.h3, Math.max(0, expected * (1 + normal(forecastRng, 0, 0.12))))
    const count = poisson(rng, expected * shock)
    observedByZone.set(zone.h3, count)
    for (let i = 0; i < count; i += 1) {
      const origin = jitterOnLand(rng, zone.centroid, 0.45)
      let destination: LngLat = origin
      for (let attempt = 0; attempt < 4 && haversineKm(origin, destination) < 1.5; attempt += 1) {
        const loc = pickWeighted(rng, LOCALITIES, (l) => destinationWeight(l, kind))
        destination = jitterOnLand(rng, loc.center, loc.spreadKm * 0.9)
      }
      requests.push({
        id: '',
        createdAt: toIso(windowStart + Math.round(sampleMinute(rng, kind, horizonMinutes) * MINUTE)),
        origin,
        destination,
        originZone: zone.h3,
      })
    }
  }
  requests.sort((a, b) => toEpoch(a.createdAt) - toEpoch(b.createdAt) || a.origin[0] - b.origin[0])
  requests.forEach((r, i) => {
    r.id = `R-${tag}-${String(i + 1).padStart(3, '0')}`
  })

  // Frota real no início do horizonte.
  const profiles = buildFleetProfiles(experiment)
  const vehicleDays = new Map<string, VehicleDay>()
  const fleetAtStart: FleetPosition[] = []
  for (const p of profiles) {
    const vrng = createRng(`${experiment.id}:${date}:${p.vehicle.id}`)
    const present = vrng() < p.presenceRate
    const start = jitterOnLand(vrng, p.typical, 1.6)
    const roll = vrng()
    const commitment = roll < 0.18
    let availableFrom = windowStart
    if (commitment) availableFrom += Math.round(uniform(vrng, 4, 38)) * MINUTE
    else if (roll < 0.3) availableFrom += Math.round(uniform(vrng, 10, 80)) * MINUTE
    const availableUntil = vrng() < 0.15 ? windowEnd - Math.round(uniform(vrng, 20, 70)) * MINUTE : windowEnd
    vehicleDays.set(p.vehicle.id, { vehicleId: p.vehicle.id, present, start, availableFrom, availableUntil, commitment })
    if (!present) continue
    const state: VehicleState = availableFrom > windowStart ? (commitment ? 'on_trip' : 'unavailable') : 'idle'
    fleetAtStart.push({
      vehicleId: p.vehicle.id,
      position: start,
      zone: cellOf(start, res),
      basis: 'observed_start',
      availableFrom: toIso(availableFrom),
      availableUntil: toIso(availableUntil),
      state,
    })
  }

  const zones: DemandZone[] = seeds.map((z) => ({
    h3: z.h3,
    centroid: z.centroid,
    locality: z.locality.name,
    municipality: z.locality.municipality,
    forecastRides: Math.round((forecastByZone.get(z.h3) ?? 0) * 10) / 10,
    observedRides: observedByZone.get(z.h3) ?? 0,
  }))

  const world: DemoWorld = {
    experiment,
    windowStart,
    windowEnd,
    cutoff,
    profiles,
    vehicleDays,
    snapshot: {
      experimentId: experiment.id,
      date,
      cutoff: toIso(cutoff),
      window: { start: toIso(windowStart), end: toIso(windowEnd) },
      zones,
      vehicles: profiles.map((p) => p.vehicle),
      predictedFleet: [],
      fleetAtStart,
      requests,
      forecastTotal: Math.round(zones.reduce((s, z) => s + z.forecastRides, 0) * 10) / 10,
      observedTotal: requests.length,
      provenance: experiment.provenance,
    },
  }
  world.snapshot.predictedFleet = predictedFleet(world, params)
  worldCache.set(key, world)
  return world
}

/** Assinatura das entradas comuns (pedidos + frota real); idêntica entre cenários do mesmo dia. */
export function inputSignature(world: DemoWorld): string {
  const s = world.snapshot
  const payload = JSON.stringify({
    e: s.experimentId,
    d: s.date,
    r: s.requests.map((r) => [r.id, r.createdAt, r.origin, r.destination]),
    f: s.fleetAtStart.map((f) => [f.vehicleId, f.position, f.availableFrom, f.availableUntil]),
  })
  return `${shortHash(payload)}${shortHash(`${payload}#`)}`.slice(0, 12)
}

// ---------------------------------------------------------------------------------------------
// Plano demonstrativo (só com informação do corte)
// ---------------------------------------------------------------------------------------------

/**
 * Rotina genérica de movimentos ilustrativos. Recebe APENAS a previsão por zona e a frota prevista
 * — o que se conhece no corte. Não recebe pedidos observados, então não há vazamento de D+1.
 */
export function planDemoMoves(
  forecast: readonly Pick<DemandZone, 'h3' | 'centroid' | 'forecastRides'>[],
  fleet: readonly FleetPosition[],
  profile: { moveFraction: number; focus: number; distanceScaleKm: number },
  maxRepositionKm: number,
  rng: Rng,
): PlannedMove[] {
  const total = forecast.reduce((s, z) => s + z.forecastRides, 0)
  if (total <= 0 || fleet.length === 0) return []
  const desired = new Map(forecast.map((z) => [z.h3, (z.forecastRides / total) * fleet.length]))
  const counts = new Map<string, number>()
  for (const v of fleet) counts.set(v.zone, (counts.get(v.zone) ?? 0) + 1)
  const surplusOf = (zone: string) => (counts.get(zone) ?? 0) - (desired.get(zone) ?? 0)
  const order = [...fleet]
    .map((v) => ({ v, key: surplusOf(v.zone) + rng() * 0.5 }))
    .sort((a, b) => b.key - a.key)
    .map((x) => x.v)
  const limit = Math.round(fleet.length * profile.moveFraction)
  const moves: PlannedMove[] = []
  for (const v of order) {
    if (moves.length >= limit) break
    if (surplusOf(v.zone) < 0.25) continue
    const options = forecast
      .map((z) => ({ z, deficit: -surplusOf(z.h3), km: haversineKm(v.position, z.centroid) }))
      .filter((o) => o.deficit > 0.3 && o.km >= 0.8 && o.km <= maxRepositionKm)
    if (options.length === 0) continue
    const choice = pickWeighted(rng, options, (o) => o.deficit ** profile.focus * Math.exp(-o.km / profile.distanceScaleKm))
    counts.set(v.zone, (counts.get(v.zone) ?? 0) - 1)
    counts.set(choice.z.h3, (counts.get(choice.z.h3) ?? 0) + 1)
    moves.push({ vehicleId: v.vehicleId, from: v.position, fromZone: v.zone, toZone: choice.z.h3, to: choice.z.centroid })
  }
  return moves
}

function bendFor(id: string): number {
  const h = hashString(id)
  return ((h & 1) === 0 ? 1 : -1) * (0.12 + ((h >>> 1) % 100) / 1000)
}

function materialize(
  world: DemoWorld,
  algorithmId: ProposedAlgorithmId,
  moves: readonly PlannedMove[],
  params: ExperimentParameters,
): RepositionMovement[] {
  const tolerance = params.executionToleranceMinutes * MINUTE
  const speed = params.speedKmh
  return moves.map((m, i) => {
    const id = `M-${algorithmId.slice(0, 3).toUpperCase()}-${String(i + 1).padStart(2, '0')}`
    const vd = world.vehicleDays.get(m.vehicleId)
    let outcome: ExecutionOutcome = 'executed'
    if (!vd || !vd.present) outcome = 'driver_absent'
    else if (vd.availableFrom > world.windowStart + tolerance) outcome = vd.commitment ? 'driver_on_trip' : 'availability_conflict'
    else if (vd.availableUntil < world.windowStart + 45 * MINUTE) outcome = 'availability_conflict'
    const plannedKm = haversineKm(m.from, m.to)
    const bend = bendFor(id)
    const base: RepositionMovement = {
      id,
      algorithmId,
      vehicleId: m.vehicleId,
      plannedFrom: m.from,
      executedFrom: null,
      to: m.to,
      fromZone: m.fromZone,
      toZone: m.toZone,
      plannedKm,
      executedKm: null,
      plannedAt: toIso(world.cutoff),
      scheduledStart: toIso(world.windowStart),
      outcome,
      executedStart: null,
      executedEnd: null,
      plannedPath: illustrativeCurve(m.from, m.to, bend),
      executedPath: null,
      pathKind: 'illustrative',
    }
    if (outcome !== 'executed' || !vd) return base
    const start = Math.max(world.windowStart, vd.availableFrom)
    const km = haversineKm(vd.start, m.to)
    const end = start + Math.round((km / speed) * HOUR)
    return {
      ...base,
      executedFrom: vd.start,
      executedKm: km,
      executedStart: toIso(start),
      executedEnd: toIso(end),
      executedPath: illustrativeCurve(vd.start, m.to, bend),
    }
  })
}

// ---------------------------------------------------------------------------------------------
// Roteiro de eventos (mesmo mundo para todos os cenários)
// ---------------------------------------------------------------------------------------------

interface VehicleRuntime {
  id: string
  pos: LngLat
  freeAt: number
  until: number
}

function runScenario(
  world: DemoWorld,
  algorithmId: AlgorithmId,
  movements: readonly RepositionMovement[],
  params: ExperimentParameters,
): { events: SimulationEvent[]; metrics: ScenarioMetrics } {
  const speed = params.speedKmh
  const maxPickupKm = (params.maxPickupMinutes / 60) * speed
  const events: SimulationEvent[] = []
  let seq = 0
  const push = (e: Omit<SimulationEvent, 'id' | 'algorithmId'>) => {
    seq += 1
    events.push({ ...e, id: `${algorithmId}-${String(seq).padStart(4, '0')}`, algorithmId })
  }

  const runtime = new Map<string, VehicleRuntime>()
  for (const vd of world.vehicleDays.values()) {
    if (!vd.present) continue
    runtime.set(vd.vehicleId, { id: vd.vehicleId, pos: vd.start, freeAt: vd.availableFrom, until: vd.availableUntil })
  }

  let repositionKm = 0
  for (const m of movements) {
    if (m.outcome !== 'executed' || !m.executedStart || !m.executedEnd || !m.executedFrom) continue
    const v = runtime.get(m.vehicleId)
    if (!v) continue
    const km = m.executedKm ?? 0
    repositionKm += km
    v.pos = m.to
    v.freeAt = toEpoch(m.executedEnd)
    push({ t: m.executedStart, type: 'reposition_start', vehicleId: m.vehicleId, requestId: null, movementId: m.id, position: m.executedFrom, km })
    push({ t: m.executedEnd, type: 'reposition_end', vehicleId: m.vehicleId, requestId: null, movementId: m.id, position: m.to, km: null })
  }

  let pickupKm = 0
  let waitTotal = 0
  let served = 0
  for (const r of world.snapshot.requests) {
    const t = toEpoch(r.createdAt)
    push({ t: r.createdAt, type: 'request_created', vehicleId: null, requestId: r.id, movementId: null, position: r.origin, km: null })
    let best: VehicleRuntime | null = null
    let bestKm = Infinity
    for (const v of runtime.values()) {
      if (v.freeAt > t || t >= v.until) continue
      const d = haversineKm(v.pos, r.origin)
      if (d < bestKm || (d === bestKm && best !== null && v.id < best.id)) {
        best = v
        bestKm = d
      }
    }
    if (!best || bestKm > maxPickupKm) {
      push({ t: r.createdAt, type: 'request_unserved', vehicleId: null, requestId: r.id, movementId: null, position: r.origin, km: null })
      continue
    }
    const pickupAt = t + Math.round((bestKm / speed) * HOUR)
    const tripKm = haversineKm(r.origin, r.destination)
    const dropAt = pickupAt + BOARDING_MINUTES * MINUTE + Math.round((tripKm / speed) * HOUR)
    push({ t: r.createdAt, type: 'dispatch', vehicleId: best.id, requestId: r.id, movementId: null, position: best.pos, km: bestKm })
    push({ t: toIso(pickupAt), type: 'pickup', vehicleId: best.id, requestId: r.id, movementId: null, position: r.origin, km: null })
    push({ t: toIso(dropAt), type: 'dropoff', vehicleId: best.id, requestId: r.id, movementId: null, position: r.destination, km: tripKm })
    best.pos = r.destination
    best.freeAt = dropAt
    pickupKm += bestKm
    waitTotal += (pickupAt - t) / MINUTE
    served += 1
  }

  events.sort((a, b) => toEpoch(a.t) - toEpoch(b.t) || a.id.localeCompare(b.id))

  const requests = world.snapshot.requests.length
  const execution = emptyExecution()
  for (const m of movements) execution[m.outcome] += 1
  const emptyKmTotal = pickupKm + repositionKm
  const metrics: ScenarioMetrics = {
    algorithmId,
    requests,
    served,
    unserved: requests - served,
    coverage: requests > 0 ? served / requests : null,
    pickupKm,
    repositionKm,
    returnKm: null,
    emptyKmTotal,
    emptyKmPerServed: served > 0 ? emptyKmTotal / served : null,
    meanWaitMinutes: served > 0 ? waitTotal / served : null,
    plannedMoves: movements.length,
    executedMoves: execution.executed,
    plannedRepositionKm: movements.reduce((s, m) => s + m.plannedKm, 0),
    execution,
    distanceMethod: 'haversine',
    dataKind: 'demo',
    observedKm: null,
  }
  return { events, metrics }
}

// ---------------------------------------------------------------------------------------------
// API pública do gerador
// ---------------------------------------------------------------------------------------------

const runCache = new Map<string, ScenarioRun>()

export function buildScenarioRun(
  experiment: Experiment,
  date: string,
  algorithmId: AlgorithmId,
  overrides: Partial<ExperimentParameters> = {},
): ScenarioRun {
  const params = { ...experiment.parameters, ...overrides }
  const key = `${experiment.id}|${date}|${algorithmId}|${JSON.stringify(params)}`
  const cached = runCache.get(key)
  if (cached) return cached
  const world = buildDayWorld(experiment, date)
  let movements: RepositionMovement[] = []
  if (algorithmId !== 'baseline') {
    const fleet = predictedFleet(world, params)
    const forecast = world.snapshot.zones.map(({ h3, centroid, forecastRides }) => ({ h3, centroid, forecastRides }))
    const rng = createRng(`${experiment.id}:${date}:${algorithmId}:plan`)
    const moves = planDemoMoves(forecast, fleet, DEMO_PLAN_PROFILES[algorithmId], params.maxRepositionKm, rng)
    movements = materialize(world, algorithmId, moves, params)
  }
  const { events, metrics } = runScenario(world, algorithmId, movements, params)
  const run: ScenarioRun = {
    experimentId: experiment.id,
    date,
    algorithmId,
    metrics,
    movements,
    events,
    inputSignature: inputSignature(world),
  }
  runCache.set(key, run)
  return run
}

export function buildExperimentResults(experiment: Experiment): ExperimentResults {
  const days: DayResult[] = experiment.days.map((date) => {
    const world = buildDayWorld(experiment, date)
    const metrics = {} as Record<AlgorithmId, ScenarioMetrics>
    for (const id of experiment.algorithms) metrics[id] = buildScenarioRun(experiment, date, id).metrics
    return {
      date,
      forecastTotal: world.snapshot.forecastTotal,
      observedTotal: world.snapshot.observedTotal,
      inputSignature: inputSignature(world),
      metrics,
    }
  })
  return { experimentId: experiment.id, days, provenance: experiment.provenance }
}

export const SENSITIVITY_VARIANTS: readonly SensitivityVariant[] = [
  { id: 'default', label: 'Padrão', parameter: null, value: null, isDefault: true },
  { id: 'repos-3', label: 'Reposicionamento ≤ 3 km', parameter: 'maxRepositionKm', value: 3, isDefault: false },
  { id: 'repos-6', label: 'Reposicionamento ≤ 6 km', parameter: 'maxRepositionKm', value: 6, isDefault: false },
  { id: 'presence-75', label: 'Presença prevista ≥ 75%', parameter: 'minPresenceRate', value: 0.75, isDefault: false },
  { id: 'tolerance-0', label: 'Tolerância de execução 0 min', parameter: 'executionToleranceMinutes', value: 0, isDefault: false },
  { id: 'tolerance-60', label: 'Tolerância de execução 60 min', parameter: 'executionToleranceMinutes', value: 60, isDefault: false },
]

export function buildSensitivity(experiment: Experiment): SensitivityAnalysis {
  const proposed = experiment.algorithms.filter((a): a is ProposedAlgorithmId => a !== 'baseline')
  const results: SensitivityResult[] = []
  for (const variant of SENSITIVITY_VARIANTS) {
    const overrides: Partial<ExperimentParameters> =
      variant.parameter && variant.value !== null ? { [variant.parameter]: variant.value } : {}
    for (const algorithmId of proposed) {
      let baseKm = 0
      let propKm = 0
      let reposKm = 0
      let baseServed = 0
      let propServed = 0
      let requests = 0
      let executed = 0
      let planned = 0
      for (const date of experiment.days) {
        const b = buildScenarioRun(experiment, date, 'baseline').metrics
        const p = buildScenarioRun(experiment, date, algorithmId, overrides).metrics
        baseKm += b.emptyKmTotal
        propKm += p.emptyKmTotal
        reposKm += p.repositionKm
        baseServed += b.served
        propServed += p.served
        requests += b.requests
        executed += p.executedMoves
        planned += p.plannedMoves
      }
      results.push({
        variantId: variant.id,
        algorithmId,
        baselineEmptyKm: baseKm,
        proposedEmptyKm: propKm,
        repositionKm: reposKm,
        reductionPercent: reductionPercent(baseKm, propKm),
        baselineCoverage: requests > 0 ? baseServed / requests : null,
        proposedCoverage: requests > 0 ? propServed / requests : null,
        executedMoves: executed,
        plannedMoves: planned,
      })
    }
  }
  return { experimentId: experiment.id, variants: [...SENSITIVITY_VARIANTS], results, provenance: experiment.provenance }
}

/** Limpa caches (usado em testes). */
export function resetDemoCaches(): void {
  zoneCache.clear()
  fleetCache.clear()
  worldCache.clear()
  runCache.clear()
}
