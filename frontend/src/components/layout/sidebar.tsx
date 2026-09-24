import { Link } from '@tanstack/react-router'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  LayoutDashboard,
  FileText,
  Upload,
  UserPlus,
  UserMinus,
  Building2,
  Package,
  ScrollText,
  Users,
  CreditCard,
  LogOut,
  Ship,
  ChevronsLeft,
  ChevronsRight,
  type LucideIcon,
} from 'lucide-react'
import { useAuth } from '@/hooks/use-auth'
import { useSidebar } from '@/hooks/use-sidebar'

type RouteTo =
  | '/dashboard'
  | '/procesar'
  | '/altas'
  | '/bajas'
  | '/companias'
  | '/activos'
  | '/logs'
  | '/admin/usuarios'
  | '/planes'

const navItems: Array<{ to: RouteTo; label: string; icon: LucideIcon }> = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/procesar', label: 'Procesar PDF', icon: Upload },
  { to: '/altas', label: 'Altas', icon: UserPlus },
  { to: '/bajas', label: 'Bajas', icon: UserMinus },
  { to: '/companias', label: 'Compañías', icon: Building2 },
  { to: '/activos', label: 'Activos', icon: Package },
  { to: '/logs', label: 'Logs', icon: ScrollText },
]

export function Sidebar() {
  const { user, logout } = useAuth()
  const { collapsed, toggle, mobileOpen, closeMobile } = useSidebar()

  const isCollapsed = mobileOpen ? false : collapsed

  const renderContent = (ct: boolean, showCollapse: boolean) => {
    const baseClass = cn(
      'group relative flex items-center gap-3 rounded-md text-[13.5px] font-normal',
      'text-sidebar-foreground/85 transition-colors duration-100',
      'hover:bg-[rgb(255_255_255_/_0.06)] hover:text-sidebar-foreground',
      ct ? 'h-9 w-9 justify-center px-0' : 'px-3 py-1.5',
    )
    const activeClass = cn(
      'bg-[rgb(255_255_255_/_0.08)] text-sidebar-foreground font-semibold',
      !ct &&
        'before:absolute before:left-0 before:top-1.5 before:bottom-1.5 before:w-[3px] before:rounded-full before:bg-primary',
    )

    return (
      <>
        {/* Brand */}
        <div className={cn('flex items-center py-5', ct ? 'justify-center px-0' : 'gap-2.5 px-5')}>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary shadow-fluent-1">
            <Ship className="h-4.5 w-4.5 text-primary-foreground" strokeWidth={2.25} />
          </div>
          {!ct && (
            <div className="flex flex-col leading-tight overflow-hidden">
              <span className="fluent-subtitle text-sidebar-foreground whitespace-nowrap">
                PreCarga SHAT
              </span>
              <span className="fluent-caption text-sidebar-foreground/55 whitespace-nowrap">
                Maritime operations
              </span>
            </div>
          )}
        </div>

        <div className={cn('h-px fluent-divider', ct ? 'mx-2' : 'mx-3')} />

        {/* Primary nav */}
        <nav className={cn('flex-1 space-y-0.5 overflow-y-auto fluent-scroll', ct ? 'px-2 py-3' : 'px-3 py-3')}>
          {navItems.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={baseClass}
              activeProps={{ className: cn(baseClass, activeClass) }}
              title={ct ? item.label : undefined}
              onClick={closeMobile}
            >
              <item.icon
                className="h-4 w-4 shrink-0 opacity-80 group-hover:opacity-100"
                strokeWidth={2}
              />
              {!ct && <span className="truncate">{item.label}</span>}
            </Link>
          ))}

          {user?.admin && (
            <>
              {!ct && (
                <div className="my-3 px-1">
                  <div className="h-px fluent-divider" />
                </div>
              )}
              {ct && <div className="my-2 mx-2 h-px fluent-divider" />}
              {!ct && (
                <div className="px-2 pb-1 pt-1">
                  <span className="fluent-caption uppercase tracking-wider text-sidebar-foreground/45">
                    Administración
                  </span>
                </div>
              )}
              <Link
                to="/admin/usuarios"
                className={baseClass}
                activeProps={{ className: cn(baseClass, activeClass) }}
                title={ct ? 'Usuarios' : undefined}
                onClick={closeMobile}
              >
                <Users
                  className="h-4 w-4 shrink-0 opacity-80 group-hover:opacity-100"
                  strokeWidth={2}
                />
                {!ct && <span>Usuarios</span>}
              </Link>
            </>
          )}
        </nav>

        <div className={cn('h-px fluent-divider', ct ? 'mx-2' : 'mx-3')} />

        {/* Footer */}
        <div className={cn('space-y-0.5', ct ? 'p-2' : 'p-3')}>
          <Link
            to="/planes"
            className={baseClass}
            activeProps={{ className: cn(baseClass, activeClass) }}
            title={ct ? 'Planes' : undefined}
            onClick={closeMobile}
          >
            <CreditCard className="h-4 w-4 shrink-0 opacity-80 group-hover:opacity-100" strokeWidth={2} />
            {!ct && <span>Planes</span>}
          </Link>

          <Button
            variant="ghost"
            onClick={() => {
              closeMobile()
              logout()
            }}
            title={ct ? 'Cerrar Sesión' : undefined}
            className={cn(
              'h-auto rounded-md text-[13.5px] font-normal text-sidebar-foreground/85',
              'hover:bg-[rgb(255_255_255_/_0.06)] hover:text-sidebar-foreground',
              ct ? 'h-9 w-9 justify-center px-0' : 'w-full justify-start gap-3 px-3 py-1.5',
            )}
          >
            <LogOut className="h-4 w-4 shrink-0 opacity-80" strokeWidth={2} />
            {!ct && <span>Cerrar Sesión</span>}
          </Button>

          {showCollapse && (
            <button
              type="button"
              onClick={toggle}
              aria-label={collapsed ? 'Expandir menú' : 'Colapsar menú'}
              className={cn(
                'mt-1 flex items-center rounded-md text-[12px] text-sidebar-foreground/55',
                'transition-colors hover:bg-[rgb(255_255_255_/_0.06)] hover:text-sidebar-foreground',
                ct
                  ? 'h-8 w-8 justify-center mx-auto'
                  : 'h-7 w-full justify-center gap-1.5',
              )}
            >
              {ct ? (
                <ChevronsRight className="h-3.5 w-3.5" strokeWidth={2} />
              ) : (
                <>
                  <ChevronsLeft className="h-3.5 w-3.5" strokeWidth={2} />
                  <span>Colapsar</span>
                </>
              )}
            </button>
          )}
        </div>
      </>
    )
  }

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          'surface-acrylic sticky top-0 z-40 hidden h-screen shrink-0 flex-col border-r border-[rgb(255_255_255_/_0.06)] md:flex',
          'transition-[width] duration-200 ease-out',
          collapsed ? 'w-[64px]' : 'w-64',
        )}
      >
        {renderContent(isCollapsed, true)}
      </aside>

      {/* Mobile drawer */}
      <div
        className={cn(
          'fixed inset-0 z-50 md:hidden',
          !mobileOpen && 'pointer-events-none',
        )}
        aria-hidden={!mobileOpen}
      >
        <div
          className={cn(
            'absolute inset-0 bg-black/50 transition-opacity duration-200',
            mobileOpen ? 'opacity-100' : 'opacity-0',
          )}
          onClick={closeMobile}
        />
        <aside
          className={cn(
            'surface-acrylic absolute left-0 top-0 flex h-full w-72 flex-col border-r border-[rgb(255_255_255_/_0.06)]',
            'transition-transform duration-200 ease-out',
            mobileOpen ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          {renderContent(false, false)}
        </aside>
      </div>
    </>
  )
}