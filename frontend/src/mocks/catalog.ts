import type { Algorithm, Experiment, ExperimentParameters, Provenance } from '@/types'

/**
 * Catálogo demonstrativo. Os nomes dos algoritmos referenciam os experimentos existentes do TCC;
 * as descrições repetem apenas o que está documentado no repositório (DT001, docstrings de
 * `optimization/alternatives.py` e `docs/experimento_real.md`). Nenhum detalhe interno é presumido.
 */
export const ALGORITHMS: readonly Algorithm[] = [
  {
    id: 'baseline',
    name: 'Baseline sem reposicionamento',
    shortName: 'Baseline',
    reference: 'RN021',
    description:
      'Despacho do veículo livre mais próximo, sem fila nem reposicionamento preventivo. Simplificação de referência, não a política real.',
    repositions: false,
  },
  {
    id: 'guloso',
    name: 'Guloso (DT001)',
    shortName: 'Guloso',
    reference: 'DT001',
    description:
      'Abordagem principal acadêmica: heurística gulosa interpretável que distribui veículos elegíveis para déficits de demanda prevista, considerando a distância de reposicionamento.',
    repositions: true,
  },
  {
    id: 'proporcional',
    name: 'Proporcional',
    shortName: 'Proporcional',
    reference: null,
    description:
      'Regra simples de comparação: vagas por zona proporcionais à demanda prevista, preenchidas pelo par veículo–vaga mais próximo.',
    repositions: true,
  },
  {
    id: 'atribuicao_otima',
    name: 'Atribuição ótima',
    shortName: 'Atribuição',
    reference: null,
    description:
      'Método exato para a mesma meta de vagas: preenche o máximo de vagas com a menor soma de quilômetros.',
    repositions: true,
  },
]

export const DEMO_GENERATED_AT = '2026-10-15T00:00:00-03:00'

export const DEMO_DISCLAIMER =
  'Dados fictícios gerados localmente para demonstração visual. Não são medições da empresa nem resultados do TCC.'

export function demoProvenance(seed: number): Provenance {
  return {
    kind: 'demo',
    source: 'Gerador demonstrativo local (frontend/src/mocks)',
    generatedAt: DEMO_GENERATED_AT,
    disclaimer: DEMO_DISCLAIMER,
    seed,
  }
}

export const DEFAULT_PARAMETERS: ExperimentParameters = {
  cutoffHour: 20,
  planHour: 7,
  horizonHours: 3,
  lookbackDays: 56,
  maxRepositionKm: 12,
  minPresenceRate: 0.5,
  executionToleranceMinutes: 30,
  maxPickupMinutes: 25,
  speedKmh: 22,
}

/** Semana fictícia (seg–dom), deliberadamente fora de qualquer período real. */
export const DEMO_DAYS = ['2030-01-07', '2030-01-08', '2030-01-09', '2030-01-10', '2030-01-11', '2030-01-12', '2030-01-13']

export const EXPERIMENTS: readonly Experiment[] = [
  {
    id: 'demo-manha',
    name: 'Janela da manhã · 07–10h',
    description:
      'Plano preventivo calculado no corte de D às 20h e avaliado no replay de 07:00–10:00 de D+1, contra o baseline sem reposicionamento.',
    timezone: 'America/Sao_Paulo',
    region: 'Grande Vitória (ES)',
    h3Resolution: 7,
    distanceMethod: 'haversine',
    days: DEMO_DAYS,
    parameters: { ...DEFAULT_PARAMETERS },
    algorithms: ['baseline', 'guloso', 'proporcional', 'atribuicao_otima'],
    provenance: demoProvenance(20300107),
  },
  {
    id: 'demo-tarde',
    name: 'Janela da tarde · 17–20h',
    description:
      'Mesmo desenho com plano para 17:00–20:00 de D+1. O corte permanece em D às 20h, antes de todo o horizonte avaliado.',
    timezone: 'America/Sao_Paulo',
    region: 'Grande Vitória (ES)',
    h3Resolution: 7,
    distanceMethod: 'haversine',
    days: DEMO_DAYS,
    parameters: { ...DEFAULT_PARAMETERS, planHour: 17 },
    algorithms: ['baseline', 'guloso', 'proporcional', 'atribuicao_otima'],
    provenance: demoProvenance(20300117),
  },
]
