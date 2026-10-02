import { lazy, Suspense } from 'react'
import {
  createRootRouteWithContext,
  createRoute,
  createRouter,
  redirect,
  Outlet,
} from '@tanstack/react-router'
import { AppLayout } from '@/components/layout/app-layout'
import type { Usuario } from '@/types'

interface RouterContext {
  auth: {
    isAuthenticated: boolean
    isLoading: boolean
    user: Usuario | null
    whenReady: () => Promise<void>
  }
}

const rootRoute = createRootRouteWithContext<RouterContext>()({
  component: () => <Outlet />,
})

const protectedLayout = createRoute({
  getParentRoute: () => rootRoute,
  id: 'protected',
  component: AppLayout,
  beforeLoad: async ({ context }) => {
    // ESPERA a que /api/auth/me resuelva. Antes devolvia temprano si
    // isLoading, lo que dejaba entrar a rutas protegidas sin sesion
    // durante la carga (y en un refresh duro se veía un dashboard roto).
    await context.auth.whenReady()
    if (!context.auth.isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
})

const Landing = lazy(() => import('@/routes/landing'))
const Login = lazy(() => import('@/routes/login'))
const Registro = lazy(() => import('@/routes/registro'))
const Verificar = lazy(() => import('@/routes/verificar'))
const Dashboard = lazy(() => import('@/routes/dashboard'))
const Procesar = lazy(() => import('@/routes/procesar'))
const Altas = lazy(() => import('@/routes/altas'))
const Bajas = lazy(() => import('@/routes/bajas'))
const Companias = lazy(() => import('@/routes/companias'))
const Activos = lazy(() => import('@/routes/activos'))
const Logs = lazy(() => import('@/routes/logs'))
const AdminUsuarios = lazy(() => import('@/routes/admin-usuarios'))
const Planes = lazy(() => import('@/routes/planes'))
const Checkout = lazy(() => import('@/routes/checkout'))
const StripeSuccess = lazy(() => import('@/routes/stripe-success'))
const StripeCancel = lazy(() => import('@/routes/stripe-cancel'))

function RouteFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <div className="flex items-center gap-2 text-muted-foreground">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        Cargando...
      </div>
    </div>
  )
}

function LazyRoute({ component: Component }: { component: React.LazyExoticComponent<React.ComponentType> }) {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Component />
    </Suspense>
  )
}

const landingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: () => <LazyRoute component={Landing} />,
})

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: () => <LazyRoute component={Login} />,
  beforeLoad: ({ context }) => {
    if (context.auth.isAuthenticated) throw redirect({ to: '/dashboard' })
  },
})

const registroRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/registro',
  component: () => <LazyRoute component={Registro} />,
})

const verificarRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/verificar',
  component: () => <LazyRoute component={Verificar} />,
})

const dashboardRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/dashboard',
  component: () => <LazyRoute component={Dashboard} />,
})

const procesarRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/procesar',
  component: () => <LazyRoute component={Procesar} />,
})

const altasRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/altas',
  component: () => <LazyRoute component={Altas} />,
})

const bajasRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/bajas',
  component: () => <LazyRoute component={Bajas} />,
})

const companiasRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/companias',
  component: () => <LazyRoute component={Companias} />,
})

const activosRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/activos',
  component: () => <LazyRoute component={Activos} />,
})

const logsRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/logs',
  component: () => <LazyRoute component={Logs} />,
})

const adminUsuariosRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/admin/usuarios',
  component: () => <LazyRoute component={AdminUsuarios} />,
})

const planesRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/planes',
  component: () => <LazyRoute component={Planes} />,
})

const checkoutRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/checkout',
  component: () => <LazyRoute component={Checkout} />,
})

const stripeSuccessRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/stripe/success',
  component: () => <LazyRoute component={StripeSuccess} />,
})

const stripeCancelRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/stripe/cancel',
  component: () => <LazyRoute component={StripeCancel} />,
})

const routeTree = rootRoute.addChildren([
  landingRoute,
  loginRoute,
  registroRoute,
  verificarRoute,
  protectedLayout.addChildren([
    dashboardRoute,
    procesarRoute,
    altasRoute,
    bajasRoute,
    companiasRoute,
    activosRoute,
    logsRoute,
    adminUsuariosRoute,
    planesRoute,
    checkoutRoute,
    stripeSuccessRoute,
    stripeCancelRoute,
  ]),
])

export const router = createRouter({
  routeTree,
  context: {
    auth: {
      isAuthenticated: false,
      isLoading: true,
      user: null,
      // Se reemplaza en cuanto monta <RouterProvider context={...}>.
      // Antes de eso, resolver siempre (no bloquear).
      whenReady: () => Promise.resolve(),
    },
  },
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
