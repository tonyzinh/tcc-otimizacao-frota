import { NavLink } from 'react-router'
import { cn } from '@/lib/cn'
import { NAV_ITEMS } from './navigation'

export function MobileNav({ className }: { className?: string }) {
  return (
    <nav
      aria-label="Navegação principal (móvel)"
      className={cn('grid shrink-0 grid-cols-5 border-t border-line bg-surface pb-[env(safe-area-inset-bottom)]', className)}
    >
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/'}
          className={({ isActive }) =>
            cn(
              'flex flex-col items-center gap-1 py-2 text-[10px] text-fg-subtle transition-colors',
              isActive ? 'text-fg' : 'hover:text-fg-muted',
            )
          }
        >
          {({ isActive }) => (
            <>
              <item.icon className={cn('size-[18px]', isActive && 'text-brand')} strokeWidth={1.75} />
              {item.short}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}
