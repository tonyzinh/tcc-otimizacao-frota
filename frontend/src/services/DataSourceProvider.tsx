import { createContext, useContext, type ReactNode } from 'react'
import type { FleetLabDataSource } from './dataSource'

const DataSourceContext = createContext<FleetLabDataSource | null>(null)

export function DataSourceProvider({ source, children }: { source: FleetLabDataSource; children: ReactNode }) {
  return <DataSourceContext.Provider value={source}>{children}</DataSourceContext.Provider>
}

export function useDataSource(): FleetLabDataSource {
  const source = useContext(DataSourceContext)
  if (!source) throw new Error('useDataSource precisa de <DataSourceProvider>')
  return source
}
