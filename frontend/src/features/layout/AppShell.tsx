import { motion } from 'motion/react'
import { Suspense } from 'react'
import { Outlet, useLocation } from 'react-router'
import { Skeleton } from '@/components/ui/feedback'
import { DataErrorBanner } from '@/features/shared/DataNotice'
import { MobileNav } from './MobileNav'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

function PageFallback() {
  return (
    <div className="grid gap-3 p-5">
      <Skeleton className="h-6 w-48" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  )
}

export function AppShell() {
  const location = useLocation()
  return (
    <div className="flex h-dvh overflow-hidden bg-canvas text-fg">
      <Sidebar className="hidden md:flex" />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <DataErrorBanner />
        <main className="relative min-h-0 flex-1">
          <Suspense fallback={<PageFallback />}>
            <motion.div
              key={location.pathname}
              className="h-full"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22, ease: [0.2, 0.7, 0.2, 1] }}
            >
              <Outlet />
            </motion.div>
          </Suspense>
        </main>
        <MobileNav className="md:hidden" />
      </div>
    </div>
  )
}
