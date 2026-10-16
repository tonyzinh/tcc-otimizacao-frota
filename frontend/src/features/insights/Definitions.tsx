import { useStudyKind } from '@/features/shared/ExperimentContext'

const DEFINITIONS = [
  {
    term: 'Pickup',
    text: 'Deslocamento vazio do veículo livre até a origem do passageiro. Distância estimada (DIST) entre posição e origem.',
    tag: 'estimado',
  },
  {
    term: 'Reposicionamento',
    text: 'Deslocamento preventivo executado no replay. Entra no total mesmo quando não gera ganho (RN031).',
    tag: 'estimado',
  },
  { term: 'Retorno', text: 'Não calculado: ausente, não zero observado.', tag: 'ausente' },
  {
    term: 'KM vazio total',
    text: 'Pickup + reposicionamento. Definição acadêmica provisória; o KPI corporativo segue em aberto (DT003).',
    tag: 'provisório',
  },
  {
    term: 'Redução relativa',
    text: '(baseline − proposto) / baseline × 100, só com baseline positivo. Positivo = menos KM vazio.',
    tag: 'derivado',
  },
  { term: 'Cobertura', text: 'Atendidas / solicitações do replay. Controle: o plano não deve piorá-la.', tag: 'controle' },
] as const

export function Definitions() {
  const { distance } = useStudyKind()
  return (
    <dl className="divide-y divide-line">
      {DEFINITIONS.map((d) => (
        <div key={d.term} className="grid gap-1 px-4 py-2.5">
          <dt className="flex items-center justify-between gap-2">
            <span className="text-[13px] font-medium text-fg">{d.term}</span>
            <span className="rounded border border-line px-1.5 py-px text-[10px] text-fg-subtle">{d.tag}</span>
          </dt>
          <dd className="text-xs text-fg-subtle">{d.text.replace('DIST', distance)}</dd>
        </div>
      ))}
    </dl>
  )
}
