import { BookOpenText, FlaskConical } from 'lucide-react'
import { useStudyKind } from '@/features/shared/ExperimentContext'

const DEMO = [
  'Todos os números desta interface vêm de um gerador local determinístico e são fictícios.',
  'Os movimentos de cada estratégia são ilustrativos: não executam o guloso, o proporcional nem a atribuição ótima do núcleo Python.',
  'Trajetos são curvas desenhadas para leitura visual; as distâncias reportadas são Haversine entre pontos, nunca medidas sobre o desenho.',
  'Indicadores de concentração (top 5 zonas) são descritivos visuais e não fazem parte da avaliação do TCC.',
]

const METHOD = [
  'Linha reta e velocidade constante calibrada; sem rotas viárias nem trânsito (RN012).',
  'Baseline simplificado: veículo livre mais próximo, sem fila. Não é a política real da operação (RN021).',
  'Demanda atendida, não total: pedidos não atendidos na operação não têm origem registrada.',
  'Retorno à base não é medido; o KPI corporativo de KM morto segue pendente (DT003).',
  'Ganho simulado não é economia observada; valores em R$ ficam fora sem custo marginal validado.',
  'O replay mede o modelo, não a operação: não há adesão real nem reação dos motoristas.',
]

const REAL = [
  'Pedidos e posições de motoristas reais, pseudonimizados (rótulos M-xxx e P-xxxx), servidos só na máquina local.',
  'Os movimentos vêm dos algoritmos do núcleo Python (guloso de valor marginal, proporcional e regra de limiar) e do simulador calibrado, com os parâmetros congelados do final-run.',
  'Trajetos são segmentos desenhados para leitura visual; os km vêm dos eventos (Haversine × fator rua/reta), nunca do desenho.',
  'Corridas externas (agendadas e fora da janela) ocupam o motorista no simulador, mas não aparecem como trajeto no mapa.',
  'Indicadores de concentração (top 5 zonas) são descritivos visuais e não fazem parte da avaliação do TCC.',
]

const METHOD_REAL = [
  'Linha reta × fator rua/reta calibrado e velocidade constante; sem rotas nem trânsito (RN012).',
  'Baseline simulado com raio, fila e paciência calibrados ao aceite observado; não é a política real (RN021).',
  'Demanda total: inclui pedidos não atendidos, com origem própria.',
  'Retorno não é medido; o KPI corporativo de KM morto segue pendente (DT003).',
  'Ganho simulado não é economia observada; sem custo por km nem margem, não há valores em R$.',
  'A adesão segue a regra de execução do regime; motoristas ociosos ficam parados no simulador.',
]

export function Limitations() {
  const { real } = useStudyKind()
  const local = real ? REAL : DEMO
  const method = real ? METHOD_REAL : METHOD
  return (
    <div className="grid gap-px bg-line md:grid-cols-2">
      <section className="bg-surface p-4">
        <h3 className="mb-2 flex items-center gap-2 text-[13px] font-medium text-fg">
          <FlaskConical className="size-3.5 text-warning" aria-hidden /> {real ? 'Desta visualização' : 'Desta demonstração'}
        </h3>
        <ul className="grid gap-1.5 text-xs text-fg-muted">
          {local.map((item) => (
            <li key={item} className="flex gap-2">
              <span className="mt-1.5 size-1 shrink-0 rounded-full bg-fg-subtle" aria-hidden />
              {item}
            </li>
          ))}
        </ul>
      </section>
      <section className="bg-surface p-4">
        <h3 className="mb-2 flex items-center gap-2 text-[13px] font-medium text-fg">
          <BookOpenText className="size-3.5 text-fg-subtle" aria-hidden /> Do método do TCC
        </h3>
        <ul className="grid gap-1.5 text-xs text-fg-muted">
          {method.map((item) => (
            <li key={item} className="flex gap-2">
              <span className="mt-1.5 size-1 shrink-0 rounded-full bg-fg-subtle" aria-hidden />
              {item}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
