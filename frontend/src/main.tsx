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

/* ────────────────────────────────────────────────────────────
   PWA: registro del service worker.

   Va despues de render() a proposito. El registro descarga el sw.js y es
   trabajo de red: si se espera a que termine, la app tarda mas en pintar en
   la primera carga, que es justo cuando el usuario esta mirando la pantalla
   de carga. Registrando en paralelo, la instalacion ocurre mientras la app ya
   esta siendo usable.

   Solo se registra en produccion. En desarrollo Vite sirve los modulos con su
   propio HMR y un service worker cacheando /src/ sirve de estorbo.
   ──────────────────────────────────────────────────────────── */
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // Silencioso a proposito: si falla (http, extension, navegador sin SW),
      // la app sigue funcionando igual. Solo se pierde la instalabilidad.
    })
  })
}

createRoot(document.getElementById('root')!).render(<App />)
