import { FileSearch } from 'lucide-react'
import { useMemo, useState } from 'react'
import { CoverageChart } from '@/components/charts/CoverageChart'
import { ExecutionChart } from '@/components/charts/ExecutionChart'
import { NetEffectChart } from '@/components/charts/NetEffectChart'
import { SensitivityChart } from '@/components/charts/SensitivityChart'
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/feedback'
import { Panel, PanelBody, PanelHeader } from '@/components/ui/panel'
import { Segmented } from '@/components/ui/segmented'
import { AlgorithmSwatch, AlgorithmTag } from '@/features/shared/AlgorithmTag'
import { DemoStrip } from '@/features/shared/DataNotice'
import { useExperimentContext } from '@/features/shared/ExperimentContext'
import { PageHeader } from '@/features/shared/PageHeader'
import { useExperimentResults, useSensitivity } from '@/features/shared/useStudyData'
import { cn } from '@/lib/cn'
import { formatKm, formatPercent, formatSignedPercent } from '@/lib/format'
import { aggregateByAlgorithm, compareScenario } from '@/lib/metrics'
import type { ProposedAlgorithmId, SensitivityAnalysis } from '@/types'
import { Definitions } from './Definitions'
import { Limitations } from './Limitations'

function SensitivityTable({
  analysis,
  algorithms,
  names,
  shortNames,
}: {
  analysis: SensitivityAnalysis
  algorithms: readonly ProposedAlgorithmId[]
  names: Record<string, string>
  shortNames: Record<string, string>
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[340px] border-collapse text-xs">
        <caption className="sr-only">Redução do KM vazio por variação de parâmetro</caption>
        <thead>
          <tr className="border-b border-line">
            <th scope="col" className="eyebrow px-2.5 py-2 text-left font-medium">
              Variação
            </th>
            {algorithms.map((id) => (
              <th key={id} scope="col" className="eyebrow px-2 py-2 text-right font-medium" title={names[id]}>
                <span className="inline-flex items-center gap-1.5">
                  <AlgorithmSwatch id={id} />
                  {shortNames[id]}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {analysis.variants.map((v) => (
            <tr key={v.id} className="border-b border-line last:border-b-0 tabular">
              <th scope="row" className={cn('px-2.5 py-2 text-left font-normal', v.isDefault ? 'text-fg' : 'text-fg-muted')}>
                {v.label}
              </th>
              {algorithms.map((id) => {
                const r = analysis.results.find((x) => x.variantId === v.id && x.algorithmId === id)
                const value = r?.reductionPercent ?? null
                return (
                  <td
                    key={id}
                    className={cn(
                      'px-2 py-2 text-right whitespace-nowrap',
                      value === null ? 'text-fg-subtle' : value > 0 ? 'text-success-text' : 'text-critical-text',
                    )}
                    title={r ? `Cobertura ${formatPercent(r.proposedCoverage)} · reposic. ${formatKm(r.repositionKm, 0)}` : undefined}
                  >
                    {formatSignedPercent(value)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function InsightsPage() {
  const { experiment, names, shortNames } = useExperimentContext()
  const results = useExperimentResults(experiment?.id)
  const sensitivity = useSensitivity(experiment?.id)
  const algorithms = useMemo(() => experiment?.algorithms ?? [], [experiment])
  const proposed = useMemo(() => algorithms.filter((a): a is ProposedAlgorithmId => a !== 'baseline'), [algorithms])
  const [focus, setFocus] = useState<ProposedAlgorithmId>('guloso')
  const aggregated = useMemo(() => (results.data ? aggregateByAlgorithm(results.data.days, algorithms) : {}), [results.data, algorithms])
  const comparison = aggregated.baseline && aggregated[focus] ? compareScenario(aggregated.baseline, aggregated[focus]) : null

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto grid max-w-[1400px] gap-4 p-4 md:p-6">
        <PageHeader
          title="Experiment Insights"
          description="Comparações científicas do plano preventivo D+1: efeito líquido, sensibilidade, cobertura, execução das recomendações e limitações."
        />
        <DemoStrip />

        {results.error ? (
          <Panel>
            <ErrorState error={results.error} />
          </Panel>
        ) : !results.data ? (
          <div className="grid gap-4 lg:grid-cols-3">
            <Skeleton className="h-[340px] lg:col-span-2" />
            <Skeleton className="h-[340px]" />
          </div>
        ) : (
          <>
            <div className="grid gap-4 lg:grid-cols-3">
              <Panel className="lg:col-span-2">
                <PanelHeader
                  title="Efeito líquido sobre o KM vazio"
                  description="Do baseline ao cenário proposto: variação de pickup e reposicionamento somado. Período inteiro."
                  actions={
                    <Segmented<ProposedAlgorithmId>
                      label="Estratégia analisada"
                      size="sm"
                      value={focus}
                      onValueChange={setFocus}
                      options={proposed.map((id) => ({ value: id, label: <AlgorithmTag id={id} name={names[id]} /> }))}
                    />
                  }
                />
                <PanelBody>
                  {comparison ? (
                    <>
                      <NetEffectChart comparison={comparison} name={names[focus]} />
                      <p className="mt-2 text-xs text-fg-subtle">
                        Resultado:{' '}
                        <span className={cn('font-medium', (comparison.reductionPercent ?? 0) > 0 ? 'text-success-text' : 'text-critical-text')}>
                          {formatSignedPercent(comparison.reductionPercent)}
                        </span>{' '}
                        de redução do KM vazio, cobertura {formatPercent(comparison.baseline.coverage)} →{' '}
                        {formatPercent(comparison.proposed.coverage)}. Olhar só o pickup esconderia o custo do reposicionamento.
                      </p>
                    </>
                  ) : (
                    <EmptyState title="Sem comparação disponível" description="Faltam métricas do baseline ou da estratégia." />
                  )}
                </PanelBody>
              </Panel>
              <Panel>
                <PanelHeader title="Como ler o KM vazio" description="Parcelas e rótulos obrigatórios (docs/indicadores.md)." />
                <Definitions />
              </Panel>
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              <Panel className="lg:col-span-2">
                <PanelHeader
                  title="Sensibilidade dos parâmetros"
                  description="Redução do KM vazio ao variar um parâmetro por vez em relação ao padrão. Zero = sem efeito."
                />
                <PanelBody>
                  {sensitivity.data ? (
                    <SensitivityChart analysis={sensitivity.data} algorithms={proposed} names={names} />
                  ) : sensitivity.error ? (
                    <ErrorState error={sensitivity.error} />
                  ) : (
                    <Skeleton className="h-[300px]" />
                  )}
                </PanelBody>
              </Panel>
              <Panel>
                <PanelHeader title="Tabela de sensibilidade" description="Passe o cursor para ver cobertura e reposicionamento." />
                {sensitivity.data ? (
                  <SensitivityTable analysis={sensitivity.data} algorithms={proposed} names={names} shortNames={shortNames} />
                ) : (
                  <PanelBody>
                    <Skeleton className="h-[240px]" />
                  </PanelBody>
                )}
              </Panel>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <Panel>
                <PanelHeader title="Cobertura de atendimento" description="Controle da comparação, por dia. Baseline tracejado." />
                <PanelBody>
                  <CoverageChart days={results.data.days} algorithms={algorithms} names={names} />
                </PanelBody>
              </Panel>
              <Panel>
                <PanelHeader
                  title="Execução das recomendações"
                  description="Desfecho no replay das recomendações feitas no corte."
                />
                <PanelBody>
                  <ExecutionChart metrics={aggregated} algorithms={proposed} names={names} />
                  <div className="mt-3 rounded-lg border border-dashed border-line">
                    <EmptyState
                      className="py-5"
                      icon={<FileSearch />}
                      title="Motivos de reposicionamento indisponíveis"
                      description="O contrato atual registra o desfecho de cada recomendação, não a justificativa. Sem dados que sustentem motivos, eles não são exibidos."
                    />
                  </div>
                </PanelBody>
              </Panel>
            </div>

            <Panel className="overflow-hidden">
              <PanelHeader
                title="Limitações dos resultados"
                description="No ensaio com dados reais documentado em docs/experimento_real.md, nenhuma configuração reduziu o KM vazio estimado. Esta tela não reproduz aqueles números."
              />
              <div className="border-t border-line">
                <Limitations />
              </div>
            </Panel>
          </>
        )}
      </div>
    </div>
  )
}
