import { GitCompareArrows, LayoutDashboard, Lightbulb, Map, RotateCcwClock, type LucideIcon } from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  short: string
  description: string
  icon: LucideIcon
}

export const NAV_ITEMS: readonly NavItem[] = [
  { to: '/', label: 'Dashboard', short: 'Visão geral', description: 'Indicadores agregados dos experimentos', icon: LayoutDashboard },
  { to: '/lab', label: 'Simulation Lab', short: 'Lab', description: 'Mapa interativo do cenário D+1', icon: Map },
  { to: '/comparison', label: 'Algorithm Comparison', short: 'Comparar', description: 'Dois mapas sincronizados', icon: GitCompareArrows },
  { to: '/replay', label: 'Historical Replay', short: 'Replay', description: 'Reprodução dos eventos simulados', icon: RotateCcwClock },
  { to: '/insights', label: 'Experiment Insights', short: 'Insights', description: 'Comparações, sensibilidade e limitações', icon: Lightbulb },
]

export function navItemFor(pathname: string): NavItem {
  return NAV_ITEMS.find((item) => (item.to === '/' ? pathname === '/' : pathname.startsWith(item.to))) ?? NAV_ITEMS[0]!
}
