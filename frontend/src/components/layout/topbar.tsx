import { useAuth } from '@/hooks/use-auth'
import { useSidebar } from '@/hooks/use-sidebar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { LogOut, CreditCard, Search, Bell, Settings, Menu } from 'lucide-react'
import { useNavigate } from '@tanstack/react-router'

export function Topbar() {
  const { user, logout } = useAuth()
  const { toggleMenu } = useSidebar()
  const navigate = useNavigate()

  return (
    <header className="surface-mica sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-[rgb(255_255_255_/_0.06)] px-4 md:px-6">
      {/* Left: hamburger + search */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={toggleMenu}
          aria-label="Alternar menú lateral"
          className="rounded-md text-muted-foreground hover:bg-[rgb(255_255_255_/_0.06)] hover:text-foreground"
        >
          <Menu className="h-4 w-4" strokeWidth={2} />
        </Button>

        <button
          type="button"
          onClick={() => navigate({ to: '/dashboard' })}
          className="group flex h-8 w-56 items-center gap-2 rounded-md border border-[rgb(255_255_255_/_0.08)] bg-[rgb(255_255_255_/_0.04)] px-3 text-left text-[13px] text-muted-foreground transition-colors hover:bg-[rgb(255_255_255_/_0.07)] sm:w-72"
        >
          <Search className="h-3.5 w-3.5 opacity-70" strokeWidth={2} />
          <span className="flex-1 truncate">Buscar solicitudes, activos…</span>
          <kbd className="hidden h-5 items-center rounded border border-[rgb(255_255_255_/_0.10)] bg-[rgb(255_255_255_/_0.04)] px-1.5 fluent-caption text-muted-foreground/80 sm:inline-flex">
            Ctrl K
          </kbd>
        </button>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 rounded-md text-muted-foreground hover:bg-[rgb(255_255_255_/_0.06)] hover:text-foreground"
          aria-label="Notificaciones"
        >
          <Bell className="h-4 w-4" strokeWidth={2} />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 rounded-md text-muted-foreground hover:bg-[rgb(255_255_255_/_0.06)] hover:text-foreground"
          aria-label="Configuración"
          onClick={() => navigate({ to: '/planes' })}
        >
          <Settings className="h-4 w-4" strokeWidth={2} />
        </Button>

        <div className="mx-2 h-5 w-px fluent-divider" />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="h-8 gap-2 rounded-md px-1.5 text-sm font-normal hover:bg-[rgb(255_255_255_/_0.06)]"
            >
              <Avatar className="h-7 w-7">
                <AvatarFallback className="bg-primary text-[12px] font-semibold text-primary-foreground">
                  {user?.nombre?.charAt(0).toUpperCase() || 'U'}
                </AvatarFallback>
              </Avatar>
              <span className="hidden text-[13px] font-medium text-foreground/90 sm:inline">
                {user?.nombre?.split(' ')[0]}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-60" align="end" sideOffset={6}>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-0.5 py-0.5">
                <p className="fluent-body-strong text-foreground">{user?.nombre}</p>
                <p className="fluent-caption text-muted-foreground">{user?.email}</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => navigate({ to: '/planes' })}>
              <CreditCard className="mr-2 h-4 w-4 opacity-80" />
              <span>Planes</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout} className="text-destructive focus:text-destructive">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Cerrar Sesión</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
