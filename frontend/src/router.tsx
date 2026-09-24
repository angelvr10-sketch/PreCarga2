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
  }
}

const rootRoute = createRootRouteWithContext<RouterContext>()({
  component: () => <Outlet />,
})

const protectedLayout = createRoute({
  getParentRoute: () => rootRoute,
  id: 'protected',
  component: AppLayout,
  beforeLoad: ({ context }) => {
    if (context.auth.isLoading) return
    if (!context.auth.isAuthenticated) {
      throw redirect({ to: '/login' })
    }
  },
})

// Routes
import Landing from '@/routes/landing'
import Login from '@/routes/login'
import Registro from '@/routes/registro'
import Verificar from '@/routes/verificar'
import Dashboard from '@/routes/dashboard'
import Procesar from '@/routes/procesar'
import Altas from '@/routes/altas'
import Bajas from '@/routes/bajas'
import Companias from '@/routes/companias'
import Activos from '@/routes/activos'
import Logs from '@/routes/logs'
import AdminUsuarios from '@/routes/admin-usuarios'
import Planes from '@/routes/planes'
import Checkout from '@/routes/checkout'
import StripeSuccess from '@/routes/stripe-success'
import StripeCancel from '@/routes/stripe-cancel'

const landingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: Landing,
})

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: Login,
  beforeLoad: ({ context }) => {
    if (context.auth.isAuthenticated) throw redirect({ to: '/dashboard' })
  },
})

const registroRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/registro',
  component: Registro,
})

const verificarRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/verificar',
  component: Verificar,
})

const dashboardRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/dashboard',
  component: Dashboard,
})

const procesarRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/procesar',
  component: Procesar,
})

const altasRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/altas',
  component: Altas,
})

const bajasRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/bajas',
  component: Bajas,
})

const companiasRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/companias',
  component: Companias,
})

const activosRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/activos',
  component: Activos,
})

const logsRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/logs',
  component: Logs,
})

const adminUsuariosRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/admin/usuarios',
  component: AdminUsuarios,
})

const planesRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/planes',
  component: Planes,
})

const checkoutRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/checkout',
  component: Checkout,
})

const stripeSuccessRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/stripe/success',
  component: StripeSuccess,
})

const stripeCancelRoute = createRoute({
  getParentRoute: () => protectedLayout,
  path: '/stripe/cancel',
  component: StripeCancel,
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
    },
  },
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
