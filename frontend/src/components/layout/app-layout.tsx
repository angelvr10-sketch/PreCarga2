import { Outlet } from '@tanstack/react-router'
import { Sidebar } from './sidebar'
import { Topbar } from './topbar'
import { ErrorBoundary } from '@/components/error-boundary'
import { ChangelogModal } from './changelog-modal'

export function AppLayout() {
  return (
    <ErrorBoundary>
      <div className="flex min-h-screen w-full">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar />
          <main className="flex-1 overflow-x-hidden px-6 py-8 md:px-10 fluent-scroll">
            <div className="mx-auto w-full max-w-7xl">
              <Outlet />
            </div>
          </main>
        </div>
        {/* modal de novedades: se controla solo, se abre en /dashboard y desde
            el item "Novedades" del sidebar */}
        <ChangelogModal />
      </div>
    </ErrorBoundary>
  )
}
