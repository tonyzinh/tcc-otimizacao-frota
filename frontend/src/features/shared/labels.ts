import type { DistanceMethod, ExecutionOutcome, VehicleState } from '@/types'
import type { RequestDisplayState } from '@/components/simulation/replayEngine'

/** Rótulo curto do método de distância (sempre estimativa, nunca odômetro). */
export function distanceLabel(method: DistanceMethod | undefined): string {
  return method === 'haversine_fator_rua' ? 'Haversine × fator rua/reta' : 'Haversine'
}

export const OUTCOME_LABELS: Record<ExecutionOutcome, string> = {
  executed: 'Executada',
  driver_absent: 'Motorista ausente',
  driver_on_trip: 'Motorista em corrida',
  availability_conflict: 'Conflito de disponibilidade',
}

export const VEHICLE_STATE_LABELS: Record<VehicleState, string> = {
  idle: 'Livre',
  repositioning: 'Reposicionando',
  to_pickup: 'A caminho (pickup)',
  on_trip: 'Em corrida',
  unavailable: 'Indisponível',
}

export const REQUEST_STATE_LABELS: Record<RequestDisplayState, string> = {
  waiting: 'Aguardando embarque',
  served: 'Atendida',
  unserved: 'Não atendida',
}

export const VEHICLE_STATES: readonly VehicleState[] = ['idle', 'repositioning', 'to_pickup', 'on_trip', 'unavailable']
