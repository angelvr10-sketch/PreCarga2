import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

interface SidebarContextValue {
  collapsed: boolean
  toggle: () => void
  setCollapsed: (v: boolean) => void
  mobileOpen: boolean
  openMobile: () => void
  closeMobile: () => void
  toggleMenu: () => void
}

const SidebarContext = createContext<SidebarContextValue | null>(null)

const STORAGE_KEY = 'shat:sidebar-collapsed'

function isDesktop() {
  return typeof window !== 'undefined' && window.matchMedia('(min-width: 768px)').matches
}

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsedState] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return window.localStorage.getItem(STORAGE_KEY) === '1'
  })
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0')
  }, [collapsed])

  return (
    <SidebarContext.Provider
      value={{
        collapsed,
        toggle: () => setCollapsedState((v) => !v),
        setCollapsed: setCollapsedState,
        mobileOpen,
        openMobile: () => setMobileOpen(true),
        closeMobile: () => setMobileOpen(false),
        toggleMenu: () => {
          if (isDesktop()) {
            setCollapsedState((v) => !v)
          } else {
            setMobileOpen((v) => !v)
          }
        },
      }}
    >
      {children}
    </SidebarContext.Provider>
  )
}

export function useSidebar() {
  const ctx = useContext(SidebarContext)
  if (!ctx) throw new Error('useSidebar must be used within SidebarProvider')
  return ctx
}