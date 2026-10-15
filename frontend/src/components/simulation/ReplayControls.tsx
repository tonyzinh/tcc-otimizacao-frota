import { Pause, Play, SkipBack, SkipForward, StepBack, StepForward } from 'lucide-react'
import { useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Segmented } from '@/components/ui/segmented'
import { Tooltip } from '@/components/ui/tooltip'
import { formatClock } from '@/lib/format'
import { REPLAY_SPEEDS, type ReplayClock, type ReplaySpeed } from './useReplayClock'

/**
 * Controles do replay: início, evento anterior, play/pause, próximo evento, fim e velocidade.
 * Atalhos: espaço (play/pause), ← / → (evento anterior/seguinte), Home/End.
 */
export function ReplayControls({
  clock,
  onPreviousEvent,
  onNextEvent,
  keyboard = true,
}: {
  clock: ReplayClock
  onPreviousEvent: () => void
  onNextEvent: () => void
  keyboard?: boolean
}) {
  const { toggle, seek, start, end } = clock

  useEffect(() => {
    if (!keyboard) return
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      if (target && (target.closest('input, textarea, select, [role="slider"], [role="combobox"], [contenteditable]') || e.metaKey || e.ctrlKey)) return
      if (e.key === ' ') {
        e.preventDefault()
        toggle()
      } else if (e.key === 'ArrowRight') {
        e.preventDefault()
        onNextEvent()
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        onPreviousEvent()
      } else if (e.key === 'Home') {
        seek(start)
      } else if (e.key === 'End') {
        seek(end)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [keyboard, toggle, seek, start, end, onNextEvent, onPreviousEvent])

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
      <div className="flex items-center gap-0.5">
        <Tooltip content="Início (Home)">
          <Button variant="ghost" size="icon-sm" aria-label="Ir para o início" onClick={() => seek(start)}>
            <SkipBack />
          </Button>
        </Tooltip>
        <Tooltip content="Evento anterior (←)">
          <Button variant="ghost" size="icon-sm" aria-label="Evento anterior" onClick={onPreviousEvent}>
            <StepBack />
          </Button>
        </Tooltip>
        <Button
          variant="primary"
          size="icon"
          className="mx-1 rounded-full"
          aria-label={clock.playing ? 'Pausar' : 'Reproduzir'}
          aria-pressed={clock.playing}
          onClick={toggle}
        >
          {clock.playing ? <Pause className="fill-current" /> : <Play className="translate-x-px fill-current" />}
        </Button>
        <Tooltip content="Próximo evento (→)">
          <Button variant="ghost" size="icon-sm" aria-label="Próximo evento" onClick={onNextEvent}>
            <StepForward />
          </Button>
        </Tooltip>
        <Tooltip content="Fim (End)">
          <Button variant="ghost" size="icon-sm" aria-label="Ir para o fim" onClick={() => seek(end)}>
            <SkipForward />
          </Button>
        </Tooltip>
      </div>
      <div className="min-w-[88px] font-mono text-[15px] font-medium text-fg tabular" aria-live="off" data-testid="replay-clock">
        {formatClock(clock.time, true)}
      </div>
      <Segmented<`${ReplaySpeed}`>
        label="Velocidade do replay"
        size="sm"
        value={`${clock.speed}`}
        onValueChange={(v) => clock.setSpeed(Number(v) as ReplaySpeed)}
        options={REPLAY_SPEEDS.map((s) => ({ value: `${s}` as `${ReplaySpeed}`, label: `${s}×`, title: `${s} s simulados por segundo` }))}
      />
    </div>
  )
}
