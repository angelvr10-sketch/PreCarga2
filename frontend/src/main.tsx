import { StrictMode, useMemo } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from '@tanstack/react-router'
import { AuthProvider, useAuth } from '@/hooks/use-auth'
import { SidebarProvider } from '@/hooks/use-sidebar'
import { router } from '@/router'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function InnerApp() {
  const { isAuthenticated, isLoading, user, whenReady } = useAuth()

  // El contexto se memoiza: sin esto, cada render de AuthProvider le
  // pasa un objeto nuevo a RouterProvider y se pierde la memoizacion
  // del router entero.
  const context = useMemo(
    () => ({ auth: { isAuthenticated, isLoading, user, whenReady } }),
    [isAuthenticated, isLoading, user, whenReady],
  )

  // NO se bloquea el render esperando a auth. El guard de
  // protectedLayout.beforeLoad se encarga, asi que las rutas publicas
  // (/, /login, /registro) pintan de inmediato y los chunks lazy
  // empiezan a descargarse en paralelo con /api/auth/me.
  return <RouterProvider router={router} context={context} />
}

function App() {
  return (
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <SidebarProvider>
            <InnerApp />
          </SidebarProvider>
        </AuthProvider>
      </QueryClientProvider>
    </StrictMode>
  )
}

createRoot(document.getElementById('root')!).render(<App />)
