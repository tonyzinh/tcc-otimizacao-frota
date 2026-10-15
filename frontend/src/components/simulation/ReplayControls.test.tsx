import { act, render, renderHook, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ReplayControls } from './ReplayControls'
import { useReplayClock, type ReplayClock } from './useReplayClock'

function fakeClock(overrides: Partial<ReplayClock> = {}): ReplayClock {
  return {
    time: Date.parse('2030-01-07T07:00:00-03:00'),
    playing: false,
    speed: 60,
    start: Date.parse('2030-01-07T07:00:00-03:00'),
    end: Date.parse('2030-01-07T10:00:00-03:00'),
    play: vi.fn(),
    pause: vi.fn(),
    toggle: vi.fn(),
    seek: vi.fn(),
    setSpeed: vi.fn(),
    ...overrides,
  }
}

describe('ReplayControls', () => {
  it('aciona play, passos por evento, extremos e velocidade', async () => {
    const user = userEvent.setup()
    const clock = fakeClock()
    const prev = vi.fn()
    const next = vi.fn()
    render(
      <TooltipProvider>
        <ReplayControls clock={clock} onPreviousEvent={prev} onNextEvent={next} />
      </TooltipProvider>,
    )
    expect(screen.getByTestId('replay-clock')).toHaveTextContent('07:00:00')
    await user.click(screen.getByRole('button', { name: 'Reproduzir' }))
    expect(clock.toggle).toHaveBeenCalledTimes(1)
    await user.click(screen.getByRole('button', { name: 'Próximo evento' }))
    await user.click(screen.getByRole('button', { name: 'Evento anterior' }))
    expect(next).toHaveBeenCalledTimes(1)
    expect(prev).toHaveBeenCalledTimes(1)
    await user.click(screen.getByRole('button', { name: 'Ir para o fim' }))
    expect(clock.seek).toHaveBeenCalledWith(clock.end)
    await user.click(screen.getByRole('radio', { name: '300×' }))
    expect(clock.setSpeed).toHaveBeenCalledWith(300)
  })

  it('responde aos atalhos de teclado', async () => {
    const user = userEvent.setup()
    const clock = fakeClock()
    const next = vi.fn()
    render(
      <TooltipProvider>
        <ReplayControls clock={clock} onPreviousEvent={vi.fn()} onNextEvent={next} />
      </TooltipProvider>,
    )
    await user.keyboard(' ')
    await user.keyboard('{ArrowRight}')
    expect(clock.toggle).toHaveBeenCalled()
    expect(next).toHaveBeenCalled()
  })
})

describe('useReplayClock', () => {
  it('avança com o tempo, pausa e limita ao intervalo', () => {
    vi.useFakeTimers({ toFake: ['requestAnimationFrame', 'cancelAnimationFrame', 'performance', 'setTimeout', 'clearTimeout', 'Date'] })
    const start = 0
    const end = 3_600_000
    const { result } = renderHook(() => useReplayClock(start, end, start))
    act(() => result.current.setSpeed(60))
    act(() => result.current.play())
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(result.current.time).toBeGreaterThan(start)
    act(() => result.current.pause())
    const paused = result.current.time
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(result.current.time).toBe(paused)
    act(() => result.current.seek(end + 10_000))
    expect(result.current.time).toBe(end)
    vi.useRealTimers()
  })
})
