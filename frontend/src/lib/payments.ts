import { api } from './api'

interface Plan {
  id: string
  nombre: string
  precio: number
  descargas: number
}

interface CheckoutSession {
  url: string
  session_id: string
}

export interface Pago {
  id: number
  monto: number | null
  dias_comprados: number | null
  estado: string
  creado: string
  stripe_payment_id?: string | null
}

interface HistorialResponse {
  ok: boolean
  pagos: Pago[]
}

export const paymentsApi = {
  listPlans: () => api.get<Plan[]>('/api/planes'),

  history: () => api.get<HistorialResponse>('/api/pagos/historial'),

  createCheckout: (planId: string) =>
    api.post<CheckoutSession>('/api/checkout/stripe/create', { plan_id: planId }),

  success: (sessionId: string) =>
    api.get<{ ok: boolean; approved: boolean; payment_status: string | null }>(
      `/api/stripe/success?session_id=${encodeURIComponent(sessionId)}`,
    ),

  cancel: () => api.get<{ ok: boolean }>('/api/stripe/cancel'),
}
