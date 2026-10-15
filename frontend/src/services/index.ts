import type { FleetLabDataSource } from './dataSource'
import { createHttpDataSource } from './httpDataSource'
import { createMockDataSource } from './mockDataSource'

export type { FleetLabDataSource } from './dataSource'
export { DataSourceError } from './dataSource'
export { DataSourceProvider, useDataSource } from './DataSourceProvider'
export { useResource, type ResourceState } from './useResource'

/** Escolhe a origem dos dados pela configuração de build. O padrão é sempre o mock local. */
export function createDefaultDataSource(): FleetLabDataSource {
  const kind = import.meta.env.VITE_DATA_SOURCE ?? 'mock'
  const baseUrl = import.meta.env.VITE_API_BASE_URL
  if (kind === 'http') {
    if (!baseUrl) throw new Error('VITE_DATA_SOURCE=http exige VITE_API_BASE_URL')
    return createHttpDataSource(baseUrl)
  }
  return createMockDataSource()
}
