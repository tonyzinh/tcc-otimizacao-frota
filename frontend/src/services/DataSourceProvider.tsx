import { createContext, useContext, type ReactNode } from 'react'
import type { FleetLabDataSource } from './dataSource'

const DataSourceContext = createContext<FleetLabDataSource | null>(null)

export function DataSourceProvider({ source, children }: { source: FleetLabDataSource; children: ReactNode }) {
  return <DataSourceContext.Provider value={source}>{children}</DataSourceContext.Provider>
}

/** Fonte configurada, ou `null` fora do provedor (componentes isolados em testes). */
export function useOptionalDataSource(): FleetLabDataSource | null {
  return useContext(DataSourceContext)
}

export function useDataSource(): FleetLabDataSource {
  const source = useContext(DataSourceContext)
  if (!source) throw new Error('useDataSource precisa de <DataSourceProvider>')
  return source
}
