import type { AlgorithmId, ISODate } from '@/types'
import { DataSourceError, type FleetLabDataSource } from './dataSource'

/**
 * Cliente HTTP para uma futura API Python. Ainda NÃO existe backend: este módulo só define as
 * rotas esperadas para que a troca do mock seja uma mudança de configuração (`VITE_DATA_SOURCE`).
 *
 * Rotas esperadas (JSON nos contratos de `src/types/domain.ts`):
 *   GET {base}/experiments
 *   GET {base}/algorithms
 *   GET {base}/experiments/{id}/results
 *   GET {base}/experiments/{id}/days/{date}
 *   GET {base}/experiments/{id}/days/{date}/scenarios/{algorithmId}
 *   GET {base}/experiments/{id}/sensitivity
 *
 * A API deve devolver apenas agregados ou dados pseudonimizados autorizados; o frontend não deve
 * receber placas, nomes, credenciais ou coordenadas individuais sem autorização explícita.
 */
export function createHttpDataSource(baseUrl: string, options: { timeoutMs?: number } = {}): FleetLabDataSource {
  const base = baseUrl.replace(/\/+$/, '')
  const timeoutMs = options.timeoutMs ?? 15_000

  async function get<T>(path: string): Promise<T> {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      const response = await fetch(`${base}${path}`, {
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      })
      if (!response.ok) throw new DataSourceError(`Falha ao consultar ${path} (${response.status})`, response.status)
      return (await response.json()) as T
    } catch (error) {
      if (error instanceof DataSourceError) throw error
      const reason = error instanceof Error && error.name === 'AbortError' ? 'tempo esgotado' : 'API indisponível'
      throw new DataSourceError(`Não foi possível consultar ${path}: ${reason}`)
    } finally {
      clearTimeout(timer)
    }
  }

  const seg = encodeURIComponent
  return {
    kind: 'http',
    listExperiments: () => get('/experiments'),
    listAlgorithms: () => get('/algorithms'),
    getExperimentResults: (id: string) => get(`/experiments/${seg(id)}/results`),
    getDaySnapshot: (id: string, date: ISODate) => get(`/experiments/${seg(id)}/days/${seg(date)}`),
    getScenarioRun: (id: string, date: ISODate, algorithmId: AlgorithmId) =>
      get(`/experiments/${seg(id)}/days/${seg(date)}/scenarios/${seg(algorithmId)}`),
    getSensitivity: (id: string) => get(`/experiments/${seg(id)}/sensitivity`),
  }
}
