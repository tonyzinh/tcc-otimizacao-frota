import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { createMockDataSource } from './services/mockDataSource'

vi.mock('@/components/maps/FleetMap', async () => ({ default: (await import('./test/uiMocks')).FakeFleetMap }))
vi.mock('@/components/charts/EChart', async () => ({ EChart: (await import('./test/uiMocks')).FakeEChart }))

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App dataSource={createMockDataSource({ delayMs: 0 })} />
    </MemoryRouter>,
  )
}

describe('navegação', { timeout: 20_000 }, () => {
  it('abre o Dashboard com aviso de dados fictícios e resultados', async () => {
    renderAt('/')
    expect(await screen.findByRole('heading', { name: 'Visão geral dos experimentos' })).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent(/dados fictícios/i)
    expect(await screen.findByRole('table', { name: /Resultados agregados/ })).toBeInTheDocument()
    expect(screen.getAllByText('Guloso (DT001)').length).toBeGreaterThan(0)
  })

  it('navega por todas as telas pela barra lateral', async () => {
    const user = userEvent.setup()
    renderAt('/')
    await screen.findByRole('heading', { name: 'Visão geral dos experimentos' })
    const nav = screen.getByRole('navigation', { name: 'Navegação principal' })

    await user.click(within(nav).getByRole('link', { name: 'Simulation Lab' }))
    expect(await screen.findByRole('region', { name: /Mapa do Simulation Lab/ }, { timeout: 8000 })).toBeInTheDocument()

    await user.click(within(nav).getByRole('link', { name: 'Algorithm Comparison' }))
    expect(await screen.findByRole('region', { name: /cenário A/ }, { timeout: 8000 })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: /cenário B/ })).toBeInTheDocument()

    await user.click(within(nav).getByRole('link', { name: 'Historical Replay' }))
    expect(await screen.findByRole('button', { name: 'Reproduzir' }, { timeout: 8000 })).toBeInTheDocument()

    await user.click(within(nav).getByRole('link', { name: 'Experiment Insights' }))
    expect(await screen.findByRole('heading', { name: 'Experiment Insights' })).toBeInTheDocument()
    expect(await screen.findByText('Motivos de reposicionamento indisponíveis')).toBeInTheDocument()
  })

  it('mostra página de não encontrado', async () => {
    renderAt('/nao-existe')
    expect(await screen.findByText('Página não encontrada')).toBeInTheDocument()
  })
})

describe('Simulation Lab', { timeout: 20_000 }, () => {
  it('interruptores de camada alteram as camadas enviadas ao mapa', async () => {
    const user = userEvent.setup()
    renderAt('/lab')
    const map = await screen.findByTestId('fleet-map', {}, { timeout: 8000 })
    await waitFor(() => expect(map.dataset.layers).toContain('demand-hex'))
    expect(map.dataset.layers).not.toContain('flows')

    await user.click(screen.getByRole('switch', { name: /Demanda prevista \(H3\)/ }))
    await user.click(screen.getByRole('switch', { name: /Fluxos entre zonas/ }))
    await waitFor(() => {
      expect(screen.getByTestId('fleet-map').dataset.layers).not.toContain('demand-hex')
      expect(screen.getByTestId('fleet-map').dataset.layers).toContain('flows')
    })
  })

  it('o baseline não desenha reposicionamentos', async () => {
    const user = userEvent.setup()
    renderAt('/lab')
    await screen.findByTestId('fleet-map', {}, { timeout: 8000 })
    await waitFor(() => expect(screen.getByTestId('fleet-map').dataset.layers).toContain('moves-planned'))
    await user.click(screen.getByRole('combobox', { name: 'Estratégia exibida' }))
    await user.click(await screen.findByRole('option', { name: /Baseline sem reposicionamento/ }))
    await waitFor(() => expect(screen.getByTestId('fleet-map').dataset.layers).not.toContain('moves-planned'))
    expect(screen.getAllByText('Baseline sem reposicionamento').length).toBeGreaterThan(0)
  })
})

describe('tema', () => {
  it('alterna entre escuro e claro', async () => {
    const user = userEvent.setup()
    renderAt('/')
    await screen.findByRole('heading', { name: 'Visão geral dos experimentos' })
    const before = document.documentElement.dataset.theme
    await user.click(screen.getAllByRole('button', { name: 'Alternar tema' })[0]!)
    await waitFor(() => expect(document.documentElement.dataset.theme).not.toBe(before))
  })
})
