import { cn } from '@/lib/cn'

/** Marca FleetLab: hexágono (zona H3) atravessado por uma trilha de reposicionamento. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden className={cn('size-7', className)}>
      <path d="M16 3.5 26.8 9.75v12.5L16 28.5 5.2 22.25V9.75L16 3.5Z" stroke="currentColor" strokeOpacity="0.35" strokeWidth="1.5" />
      <path d="M9.5 20.5c3-1 4.2-6.8 7.4-8.1 2-.8 3.6.2 5.6-1.4" stroke="var(--brand)" strokeWidth="2" strokeLinecap="round" />
      <circle cx="9.5" cy="20.5" r="1.9" fill="currentColor" />
      <circle cx="22.5" cy="11" r="2.3" fill="var(--brand)" />
    </svg>
  )
}

export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn('flex flex-col leading-none', className)}>
      <span className="text-[13px] font-semibold tracking-tight text-fg">FleetLab</span>
      <span className="mt-0.5 text-[10px] text-fg-subtle">Mobility Intelligence</span>
    </span>
  )
}
