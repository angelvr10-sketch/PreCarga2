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

export const paymentsApi = {
  listPlans: () => api.get<Plan[]>('/api/planes'),

  createCheckout: (planId: string) =>
    api.post<CheckoutSession>('/api/checkout/stripe/create', { plan_id: planId }),

  success: (sessionId: string) =>
    api.get<{ ok: boolean }>(`/api/stripe/success?session_id=${sessionId}`),

  cancel: () => api.get<{ ok: boolean }>('/api/stripe/cancel'),
}
