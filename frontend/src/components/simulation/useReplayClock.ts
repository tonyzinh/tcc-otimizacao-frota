import { useCallback, useEffect, useRef, useState } from 'react'

export const REPLAY_SPEEDS = [30, 60, 120, 300] as const
export type ReplaySpeed = (typeof REPLAY_SPEEDS)[number]

export interface ReplayClock {
  time: number
  playing: boolean
  speed: ReplaySpeed
  start: number
  end: number
  play: () => void
  pause: () => void
  toggle: () => void
  seek: (t: number) => void
  setSpeed: (speed: ReplaySpeed) => void
}

/**
 * Relógio de reprodução baseado em requestAnimationFrame. `speed` = segundos simulados por
 * segundo real. Pausa sozinho no fim; ao dar play no fim, recomeça do início.
 */
export function useReplayClock(start: number, end: number, initial?: number): ReplayClock {
  const [time, setTime] = useState(initial ?? start)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState<ReplaySpeed>(60)
  const [range, setRange] = useState({ start, end })
  const timeRef = useRef(time)
  const speedRef = useRef(speed)

  // Nova janela (outro dia/experimento): reposiciona o relógio dentro dela.
  if (range.start !== start || range.end !== end) {
    setRange({ start, end })
    const clamped = Math.min(end, Math.max(start, time))
    setTime(clamped)
  }

  useEffect(() => {
    timeRef.current = time
  }, [time])

  useEffect(() => {
    speedRef.current = speed
  }, [speed])

  useEffect(() => {
    if (!playing) return
    let raf = 0
    let last = performance.now()
    const tick = (now: number) => {
      const dt = Math.min(100, now - last)
      last = now
      const next = Math.min(end, timeRef.current + dt * speedRef.current)
      timeRef.current = next
      setTime(next)
      if (next >= end) {
        setPlaying(false)
        return
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [playing, end])

  const play = useCallback(() => {
    if (timeRef.current >= end) {
      timeRef.current = start
      setTime(start)
    }
    setPlaying(true)
  }, [start, end])
  const pause = useCallback(() => setPlaying(false), [])
  const toggle = useCallback(() => (playing ? pause() : play()), [playing, pause, play])
  const seek = useCallback(
    (t: number) => {
      const clamped = Math.min(end, Math.max(start, t))
      timeRef.current = clamped
      setTime(clamped)
    },
    [start, end],
  )

  return { time, playing, speed, start, end, play, pause, toggle, seek, setSpeed }
}
