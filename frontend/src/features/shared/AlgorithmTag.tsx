import { cn } from '@/lib/cn'
import { SERIES_BG } from '@/theme/colors'
import type { AlgorithmId } from '@/types'

export function AlgorithmSwatch({ id, className }: { id: AlgorithmId; className?: string }) {
  return (
    <span
      aria-hidden
      className={cn('inline-block size-2 shrink-0 rounded-[2px]', SERIES_BG[id], id === 'baseline' && 'rounded-full', className)}
    />
  )
}

/** Nome da estratégia com marcador de cor (identidade nunca só pela cor). */
export function AlgorithmTag({ id, name, className }: { id: AlgorithmId; name: string; className?: string }) {
  return (
    <span className={cn('inline-flex min-w-0 items-center gap-1.5', className)}>
      <AlgorithmSwatch id={id} />
      <span className="truncate">{name}</span>
    </span>
  )
}
