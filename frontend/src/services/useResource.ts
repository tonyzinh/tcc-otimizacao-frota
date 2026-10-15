import { useEffect, useState } from 'react'

export interface ResourceState<T> {
  data: T | undefined
  error: Error | null
  loading: boolean
}

const cache = new Map<string, unknown>()

/**
 * Carrega um recurso assíncrono identificado por `key`, com cache em memória por sessão.
 * Mantém o dado anterior enquanto a nova chave carrega (sem piscar a interface).
 * `key = null` desativa a consulta.
 */
export function useResource<T>(key: string | null, load: () => Promise<T>): ResourceState<T> {
  const [state, setState] = useState<{ key: string | null; data: T | undefined; error: Error | null }>(() => ({
    key,
    data: key !== null ? (cache.get(key) as T | undefined) : undefined,
    error: null,
  }))

  const cached = key !== null && cache.has(key) ? (cache.get(key) as T) : undefined

  useEffect(() => {
    if (key === null || cache.has(key)) return
    let active = true
    load().then(
      (data) => {
        cache.set(key, data)
        if (active) setState({ key, data, error: null })
      },
      (error: unknown) => {
        if (active) setState((prev) => ({ key, data: prev.data, error: error instanceof Error ? error : new Error(String(error)) }))
      },
    )
    return () => {
      active = false
    }
    // `load` muda a cada render; a chave identifica o recurso.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  if (key === null) return { data: undefined, error: null, loading: false }
  if (cached !== undefined) return { data: cached, error: null, loading: false }
  const errorForKey = state.key === key ? state.error : null
  return { data: state.data, error: errorForKey, loading: errorForKey === null }
}

export function clearResourceCache(): void {
  cache.clear()
}
