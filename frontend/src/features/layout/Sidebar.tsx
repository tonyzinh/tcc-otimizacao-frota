import { Moon, Sun } from 'lucide-react'
import { NavLink } from 'react-router'
import { Button } from '@/components/ui/button'
import { LogoMark } from '@/components/ui/logo'
import { Tooltip } from '@/components/ui/tooltip'
import { cn } from '@/lib/cn'
import { useTheme } from '@/theme/ThemeProvider'
import { NAV_ITEMS } from './navigation'

export function Sidebar({ className }: { className?: string }) {
  const { theme, toggleTheme } = useTheme()
  return (
    <aside
      className={cn('flex w-[60px] shrink-0 flex-col items-center border-r border-line bg-surface py-3', className)}
      aria-label="Barra lateral"
    >
      <NavLink to="/" className="mb-5 flex size-9 items-center justify-center rounded-lg text-fg" aria-label="FleetLab — início">
        <LogoMark />
      </NavLink>
      <nav aria-label="Navegação principal" className="flex flex-1 flex-col items-center gap-1">
        {NAV_ITEMS.map((item) => (
          <Tooltip key={item.to} side="right" content={<span><b className="font-medium">{item.label}</b><br /><span className="text-fg-subtle">{item.description}</span></span>}>
            <NavLink
              to={item.to}
              end={item.to === '/'}
              aria-label={item.label}
              className={({ isActive }) =>
                cn(
                  'relative flex size-10 items-center justify-center rounded-lg text-fg-subtle transition-colors hover:bg-surface-raised hover:text-fg',
                  isActive && 'bg-surface-active text-fg before:absolute before:top-2.5 before:-left-[10px] before:h-5 before:w-[3px] before:rounded-r-full before:bg-brand',
                )
              }
            >
              <item.icon className="size-[18px]" strokeWidth={1.75} />
            </NavLink>
          </Tooltip>
        ))}
      </nav>
      <Tooltip side="right" content={theme === 'dark' ? 'Tema claro' : 'Tema escuro'}>
        <Button variant="ghost" size="icon" aria-label="Alternar tema" onClick={toggleTheme}>
          {theme === 'dark' ? <Sun /> : <Moon />}
        </Button>
      </Tooltip>
    </aside>
  )
}
