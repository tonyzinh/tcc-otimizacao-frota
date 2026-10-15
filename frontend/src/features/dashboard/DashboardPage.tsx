import { ArrowRight } from 'lucide-react'
import { useMemo } from 'react'
import { Link } from 'react-router'
import { DailyEmptyKmChart } from '@/components/charts/DailyEmptyKmChart'
import { DemandChart } from '@/components/charts/DemandChart'
import { KmCompositionChart } from '@/components/charts/KmCompositionChart'
import { Button } from '@/components/ui/button'
import { ErrorState, Skeleton } from '@/components/ui/feedback'
import { Panel, PanelBody, PanelHeader } from '@/components/ui/panel'
import { DemoStrip } from '@/features/shared/DataNotice'
import { useExperimentContext } from '@/features/shared/ExperimentContext'
import { PageHeader } from '@/features/shared/PageHeader'
import { ResultsTable } from '@/features/shared/ResultsTable'
import { useExperimentResults } from '@/features/shared/useStudyData'
import { aggregateByAlgorithm } from '@/lib/metrics'
import { ExperimentList } from './ExperimentList'
import { KpiStrip } from './KpiStrip'
import { StudyDesign } from './StudyDesign'

export default function DashboardPage() {
  const { experiment, experiments, setExperimentId, names } = useExperimentContext()
  const results = useExperimentResults(experiment?.id)
  const algorithms = useMemo(() => experiment?.algorithms ?? [], [experiment])
  const aggregated = useMemo(
    () => (results.data ? aggregateByAlgorithm(results.data.days, algorithms) : {}),
    [results.data, algorithms],
  )

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto grid max-w-[1400px] gap-4 p-4 md:p-6">
        <PageHeader
          title="Visão geral dos experimentos"
          description="KM vazio estimado (pickup + reposicionamento) do plano preventivo D+1 contra o baseline sem reposicionamento, com a cobertura como controle."
          actions={
            <Button asChild variant="secondary" size="sm">
              <Link to="/lab">
                Abrir Simulation Lab <ArrowRight />
              </Link>
            </Button>
          }
        />
        <DemoStrip />

        {results.error ? (
          <Panel>
            <ErrorState error={results.error} />
          </Panel>
        ) : !results.data || !experiment ? (
          <div className="grid gap-4">
            <Skeleton className="h-[104px]" />
            <div className="grid gap-4 lg:grid-cols-3">
              <Skeleton className="h-[320px] lg:col-span-2" />
              <Skeleton className="h-[320px]" />
            </div>
          </div>
        ) : (
          <>
            <KpiStrip results={results.data} aggregated={aggregated} algorithms={algorithms} names={names} />

            <div className="grid gap-4 lg:grid-cols-3">
              <Panel className="lg:col-span-2">
                <PanelHeader
                  title="KM vazio estimado por dia"
                  description="Soma Haversine de pickup e reposicionamento executado. Baseline tracejado."
                />
                <PanelBody>
                  <DailyEmptyKmChart days={results.data.days} algorithms={algorithms} names={names} />
                </PanelBody>
              </Panel>
              <Panel>
                <PanelHeader title="Composição do KM vazio" description={`${experiment.days.length} dias agregados`} />
                <PanelBody>
                  <KmCompositionChart metrics={aggregated} algorithms={algorithms} names={names} height={250} />
                </PanelBody>
              </Panel>
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              <Panel className="lg:col-span-2">
                <PanelHeader
                  title="Resultados comparativos"
                  description="Redução positiva = cenário proposto com menos KM vazio que o baseline nos mesmos pedidos e frota."
                />
                <ResultsTable days={results.data.days} aggregated={aggregated} algorithms={algorithms} names={names} />
              </Panel>
              <Panel>
                <PanelHeader title="Demanda prevista × observada" description="Previsão no corte de D; observado no replay de D+1." />
                <PanelBody>
                  <DemandChart days={results.data.days} />
                </PanelBody>
              </Panel>
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              <Panel className="lg:col-span-2">
                <PanelHeader title="Desenho do experimento" description="Como o plano preventivo é calculado e avaliado." />
                <PanelBody>
                  <StudyDesign experiment={experiment} />
                </PanelBody>
              </Panel>
              <Panel className="overflow-hidden">
                <PanelHeader title="Experimentos" description="Selecione para atualizar todas as telas." />
                <ExperimentList experiments={experiments} activeId={experiment.id} onSelect={setExperimentId} />
              </Panel>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
