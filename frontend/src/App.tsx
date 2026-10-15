import { lazy } from 'react'
import { Route, Routes } from 'react-router'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AppShell } from '@/features/layout/AppShell'
import { ExperimentProvider } from '@/features/shared/ExperimentContext'
import { NotFoundPage } from '@/features/shared/NotFoundPage'
import { DataSourceProvider, type FleetLabDataSource } from '@/services'
import { ThemeProvider } from '@/theme/ThemeProvider'

const DashboardPage = lazy(() => import('@/features/dashboard/DashboardPage'))
const SimulationLabPage = lazy(() => import('@/features/lab/SimulationLabPage'))
const ComparisonPage = lazy(() => import('@/features/comparison/ComparisonPage'))
const ReplayPage = lazy(() => import('@/features/replay/ReplayPage'))
const InsightsPage = lazy(() => import('@/features/insights/InsightsPage'))

/** Raiz sem roteador: o roteador (Browser/Memory) é injetado por `main.tsx` ou pelos testes. */
export function App({ dataSource }: { dataSource: FleetLabDataSource }) {
  return (
    <ThemeProvider>
      <DataSourceProvider source={dataSource}>
        <TooltipProvider delayDuration={250}>
          <ExperimentProvider>
            <Routes>
              <Route element={<AppShell />}>
                <Route index element={<DashboardPage />} />
                <Route path="lab" element={<SimulationLabPage />} />
                <Route path="comparison" element={<ComparisonPage />} />
                <Route path="replay" element={<ReplayPage />} />
                <Route path="insights" element={<InsightsPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Routes>
          </ExperimentProvider>
        </TooltipProvider>
      </DataSourceProvider>
    </ThemeProvider>
  )
}
