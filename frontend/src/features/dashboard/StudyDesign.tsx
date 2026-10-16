import { CalendarClock, Flag, Play, Scale } from 'lucide-react'
import { distanceLabel } from '@/features/shared/labels'
import type { Experiment } from '@/types'

/** Linha do tempo do desenho D+1: o plano usa só o que se sabe no corte. */
export function StudyDesign({ experiment }: { experiment: Experiment }) {
  const p = experiment.parameters
  const end = p.planHour + p.horizonHours
  const fleetText =
    p.regime === 'B' || p.regime === 'C'
      ? `Previsão por zona H3 r${experiment.h3Resolution}; ${p.regime === 'B' ? 'escala de D+1 conhecida' : 'frota real de D+1 (oráculo)'}.`
      : `Previsão por zona H3 r${experiment.h3Resolution} e frota prevista (presença ≥ ${Math.round(p.minPresenceRate * 100)}%).`
  const steps = [
    {
      icon: CalendarClock,
      title: p.cutoffHour >= 24 ? 'Corte · fim de D' : `Corte · D ${p.cutoffHour}h`,
      text: `Histórico de ${p.lookbackDays} dias anteriores; nada de D+1 entra no plano${p.regime === 'C' ? ' (exceto no oráculo)' : ''}.`,
    },
    { icon: Flag, title: 'Plano preventivo', text: fleetText },
    {
      icon: Play,
      title: `Replay · D+1 ${String(p.planHour).padStart(2, '0')}–${String(end).padStart(2, '0')}h`,
      text: p.executionRule ?? `Execução se o motorista estiver livre até ${p.executionToleranceMinutes} min após o início.`,
    },
    { icon: Scale, title: 'Comparação', text: `Mesmos pedidos, frota, janela e método (${distanceLabel(experiment.distanceMethod)}) em todos os cenários.` },
  ]
  return (
    <ol className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {steps.map((s, i) => (
        <li key={s.title} className="relative flex gap-3">
          <div className="flex flex-col items-center">
            <span className="flex size-7 items-center justify-center rounded-full border border-line-strong bg-surface-raised text-fg-muted">
              <s.icon className="size-3.5" aria-hidden />
            </span>
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-fg-subtle">0{i + 1}</span>
              <span className="text-[13px] font-medium text-fg">{s.title}</span>
            </div>
            <p className="mt-0.5 text-xs text-fg-subtle">{s.text}</p>
          </div>
        </li>
      ))}
    </ol>
  )
}
