/**
 * Contratos do FleetLab.
 *
 * Os nomes seguem o vocabulário do TCC (alocação preventiva D+1, KM vazio estimado) e foram
 * pensados para receber, no futuro, respostas de uma API Python. Toda medida de distância carrega
 * o método (`haversine`) e nenhuma é tratada como quilometragem observada: `observedKm` e
 * `returnKm` ficam `null` de propósito, como nos relatórios do núcleo Python.
 */

/** Data/hora ISO 8601 com deslocamento explícito, ex.: `2030-01-07T07:00:00-03:00`. */
export type ISODateTime = string
/** Data local `YYYY-MM-DD` no fuso do experimento. */
export type ISODate = string
/**
 * Método de distância. `haversine`: linha reta (dados demonstrativos e replay legado);
 * `haversine_fator_rua`: linha reta × fator rua/reta calibrado (rodada v2). Ambos são estimativas.
 */
export type DistanceMethod = 'haversine' | 'haversine_fator_rua'

/** Coordenada `[longitude, latitude]` em graus decimais (WGS84). */
export type LngLat = readonly [number, number]
/** Índice de célula H3 em hexadecimal. */
export type H3Index = string

/** Origem dos dados exibidos. A interface sempre mostra esse rótulo. */
export type DataKind = 'demo' | 'synthetic' | 'real'

export type AlgorithmId = 'baseline' | 'guloso' | 'proporcional' | 'atribuicao_otima' | 'regra_limiar'
export type ProposedAlgorithmId = Exclude<AlgorithmId, 'baseline'>

export interface Provenance {
  kind: DataKind
  /** Descrição curta da fonte, ex.: "Gerador demonstrativo local". */
  source: string
  generatedAt: ISODateTime
  /** Texto exibido junto aos dados. Obrigatório para `demo`. */
  disclaimer: string
  seed?: number
}

/** Parâmetros do desenho experimental, espelhando as opções do `gold-replay`. */
export interface ExperimentParameters {
  /** Hora local do corte em D (informação disponível até aqui). */
  cutoffHour: number
  /** Hora local de início do horizonte avaliado em D+1. */
  planHour: number
  horizonHours: number
  lookbackDays: number
  maxRepositionKm: number
  minPresenceRate: number
  executionToleranceMinutes: number
  maxPickupMinutes: number
  /** Velocidade em linha reta usada para converter distância em tempo. */
  speedKmh: number
  /** Rodada v2 (dados reais): raio de despacho, paciência, fator rua/reta, regra de execução e regime. */
  radiusKm?: number
  patienceSeconds?: number
  roadFactor?: number
  executionRule?: string
  regime?: 'A' | 'B' | 'C'
}

export interface Experiment {
  id: string
  name: string
  description: string
  timezone: string
  region: string
  h3Resolution: number
  distanceMethod: DistanceMethod
  days: ISODate[]
  parameters: ExperimentParameters
  algorithms: AlgorithmId[]
  provenance: Provenance
}

export interface Algorithm {
  id: AlgorithmId
  name: string
  shortName: string
  /** Referência documental, ex.: `DT001`. */
  reference: string | null
  description: string
  repositions: boolean
}

/** Veículo com identificador pseudônimo; nunca placa ou código interno. */
export interface Vehicle {
  id: string
  label: string
}

export interface DemandZone {
  h3: H3Index
  centroid: LngLat
  locality: string
  municipality: string
  /** Corridas previstas no horizonte, calculadas só com dados anteriores ao corte. */
  forecastRides: number
  /** Corridas observadas em D+1 (mundo do replay). */
  observedRides: number
}

export type VehicleState = 'unavailable' | 'idle' | 'repositioning' | 'to_pickup' | 'on_trip'

/** Posição de frota. `predicted` = conhecida no corte; `observed_start` = início de D+1. */
export interface FleetPosition {
  vehicleId: string
  position: LngLat
  zone: H3Index
  basis: 'predicted' | 'observed_start'
  /** Instante a partir do qual o veículo pode ser despachado. */
  availableFrom: ISODateTime
  availableUntil: ISODateTime
  state: VehicleState
}

export type ExecutionOutcome = 'executed' | 'driver_absent' | 'driver_on_trip' | 'availability_conflict'

export interface RepositionMovement {
  id: string
  algorithmId: ProposedAlgorithmId
  vehicleId: string
  /** Origem planejada (posição prevista no corte). */
  plannedFrom: LngLat
  /** Origem efetiva no replay (posição real), quando executado. */
  executedFrom: LngLat | null
  to: LngLat
  fromZone: H3Index
  toZone: H3Index
  plannedKm: number
  executedKm: number | null
  plannedAt: ISODateTime
  scheduledStart: ISODateTime
  outcome: ExecutionOutcome
  executedStart: ISODateTime | null
  executedEnd: ISODateTime | null
  /** Geometrias apenas ilustrativas (curvas), nunca rotas viárias. */
  plannedPath: LngLat[]
  executedPath: LngLat[] | null
  pathKind: 'illustrative'
}

export interface RideRequest {
  id: string
  createdAt: ISODateTime
  origin: LngLat
  destination: LngLat
  originZone: H3Index
}

export type SimulationEventType =
  | 'request_created'
  | 'reposition_start'
  | 'reposition_end'
  | 'dispatch'
  | 'pickup'
  | 'dropoff'
  | 'request_unserved'

export interface SimulationEvent {
  id: string
  t: ISODateTime
  type: SimulationEventType
  algorithmId: AlgorithmId
  vehicleId: string | null
  requestId: string | null
  movementId: string | null
  position: LngLat
  /** Distância Haversine associada ao evento (pickup, viagem ou reposicionamento). */
  km: number | null
}

export interface ScenarioMetrics {
  algorithmId: AlgorithmId
  requests: number
  served: number
  unserved: number
  /** Atendidos / pedidos; `null` sem pedidos. */
  coverage: number | null
  pickupKm: number
  repositionKm: number
  /** Retorno não é medido: ausente, não zero. */
  returnKm: null
  /** pickup + reposicionamento (definição acadêmica provisória). */
  emptyKmTotal: number
  emptyKmPerServed: number | null
  meanWaitMinutes: number | null
  plannedMoves: number
  executedMoves: number
  plannedRepositionKm: number
  execution: Record<ExecutionOutcome, number>
  distanceMethod: DistanceMethod
  dataKind: DataKind
  observedKm: null
}

export interface DayWindow {
  start: ISODateTime
  end: ISODateTime
}

export interface DaySnapshot {
  experimentId: string
  date: ISODate
  cutoff: ISODateTime
  window: DayWindow
  zones: DemandZone[]
  vehicles: Vehicle[]
  /** Frota prevista no corte (presença >= limiar), com zona típica. */
  predictedFleet: FleetPosition[]
  /** Frota real no início do horizonte (mundo do replay, igual em todos os cenários). */
  fleetAtStart: FleetPosition[]
  requests: RideRequest[]
  forecastTotal: number
  observedTotal: number
  provenance: Provenance
}

export interface ScenarioRun {
  experimentId: string
  date: ISODate
  algorithmId: AlgorithmId
  metrics: ScenarioMetrics
  movements: RepositionMovement[]
  events: SimulationEvent[]
  /** Hash das entradas comuns; cenários só são comparáveis com a mesma assinatura. */
  inputSignature: string
}

export interface DayResult {
  date: ISODate
  forecastTotal: number
  observedTotal: number
  inputSignature: string
  metrics: Record<AlgorithmId, ScenarioMetrics>
}

export interface ExperimentResults {
  experimentId: string
  days: DayResult[]
  provenance: Provenance
}

export interface SensitivityVariant {
  id: string
  label: string
  parameter: keyof ExperimentParameters | null
  value: number | null
  isDefault: boolean
}

export interface SensitivityResult {
  variantId: string
  algorithmId: ProposedAlgorithmId
  baselineEmptyKm: number
  proposedEmptyKm: number
  repositionKm: number
  /** Redução relativa (%); `null` quando o baseline não tem KM positivo. */
  reductionPercent: number | null
  baselineCoverage: number | null
  proposedCoverage: number | null
  executedMoves: number
  plannedMoves: number
}

export interface SensitivityAnalysis {
  experimentId: string
  variants: SensitivityVariant[]
  results: SensitivityResult[]
  provenance: Provenance
}

/** Estado de um veículo num instante do replay (derivado de eventos). */
export interface VehicleFrame {
  vehicleId: string
  position: LngLat
  state: VehicleState
  /** Progresso no segmento atual (0–1); útil para rótulos e depuração. */
  progress: number
}

export interface CumulativeCounters {
  pickupKm: number
  repositionKm: number
  emptyKm: number
  served: number
  unserved: number
  pending: number
}

export interface ReplayFrame {
  /** Epoch em milissegundos. */
  t: number
  vehicles: VehicleFrame[]
  /** Pedidos já criados e ainda sem embarque ou desfecho. */
  waitingRequestIds: string[]
  cumulative: CumulativeCounters
}
