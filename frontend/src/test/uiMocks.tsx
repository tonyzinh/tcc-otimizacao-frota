import type { ReactNode } from 'react'

/**
 * Substitutos de componentes que exigem WebGL/canvas (MapLibre, deck.gl, ECharts), indisponíveis
 * no jsdom. O mapa falso expõe os ids das camadas recebidas para que os testes verifiquem que
 * filtros e interruptores realmente mudam o que seria desenhado.
 */
export function FakeFleetMap({
  layers,
  ariaLabel,
  children,
}: {
  layers: readonly { id: string }[]
  ariaLabel: string
  children?: ReactNode
}) {
  return (
    <div data-testid="fleet-map" role="region" aria-label={ariaLabel} data-layers={layers.map((l) => l.id).join(',')}>
      {children}
    </div>
  )
}

export function FakeEChart({ ariaLabel }: { ariaLabel: string }) {
  return <div role="img" aria-label={ariaLabel} />
}
