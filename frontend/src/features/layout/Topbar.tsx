import { Moon, Sun } from 'lucide-react'
import { useLocation } from 'react-router'
import { Button } from '@/components/ui/button'
import { LogoMark } from '@/components/ui/logo'
import { Select } from '@/components/ui/select'
import { DataKindBadge } from '@/features/shared/DataNotice'
import { useExperimentContext } from '@/features/shared/ExperimentContext'
import { formatDay } from '@/lib/format'
import { useTheme } from '@/theme/ThemeProvider'
import { navItemFor } from './navigation'

export function Topbar() {
  const { pathname } = useLocation()
  const item = navItemFor(pathname)
  const { experiments, experiment, date, setExperimentId, setDate } = useExperimentContext()
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="flex min-h-12 shrink-0 flex-wrap items-center gap-x-3 gap-y-2 border-b border-line bg-surface/80 px-3 py-2 backdrop-blur md:px-5">
      <div className="flex min-w-0 items-center gap-2.5">
        <span className="text-fg md:hidden">
          <LogoMark className="size-6" />
        </span>
        <div className="flex min-w-0 items-center gap-1.5 text-[13px]">
          <span className="hidden text-fg-subtle sm:inline">FleetLab</span>
          <span className="hidden text-fg-subtle sm:inline" aria-hidden>
            /
          </span>
          <span className="truncate font-medium text-fg">{item.label}</span>
        </div>
      </div>
      <div className="ml-auto flex min-w-0 items-center gap-2">
        {experiment ? (
          <>
            <Select
              label="Experimento"
              size="sm"
              value={experiment.id}
              onValueChange={setExperimentId}
              triggerClassName="w-[148px] sm:w-[220px]"
              options={experiments.map((e) => ({ value: e.id, label: e.name, hint: `${e.region} · ${e.days.length} dias` }))}
            />
            {date ? (
              <Select
                label="Dia avaliado"
                size="sm"
                value={date}
                onValueChange={setDate}
                triggerClassName="w-[104px] sm:w-[128px]"
                options={experiment.days.map((d, i) => ({ value: d, label: formatDay(d), hint: `Dia ${i + 1} · corte na véspera às ${experiment.parameters.cutoffHour}h` }))}
              />
            ) : null}
          </>
        ) : null}
        <DataKindBadge provenance={experiment?.provenance} className="hidden lg:inline-flex" />
        <Button variant="ghost" size="icon-sm" className="md:hidden" aria-label="Alternar tema" onClick={toggleTheme}>
          {theme === 'dark' ? <Sun /> : <Moon />}
        </Button>
      </div>
    </header>
  )
}
