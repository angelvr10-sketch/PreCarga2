import { api } from './api'
import type { Usuario } from '@/types'

interface AuthResponse {
  ok: boolean
  mensaje?: string
  user?: Usuario
}

export const authApi = {
  login: (email: string, password: string) =>
    api.post<AuthResponse>('/api/auth/login', { email, password }),

  register: (nombre: string, email: string, password: string) =>
    api.post<AuthResponse>('/api/auth/register', { nombre, email, password }),

  verify: (email: string, codigo: string) =>
    api.post<AuthResponse>('/api/auth/verify', { email, codigo }),

  resendCode: (email: string) =>
    api.post<AuthResponse>('/api/auth/resend-code', { email }),

  changePassword: (actual: string, nueva: string) =>
    api.post<AuthResponse>('/api/auth/change-password', { actual, nueva }),

  updateProfile: (datos: { nombre?: string; email?: string; actual?: string }) =>
    api.patch<AuthResponse>('/api/auth/profile', datos),

  forgotPassword: (email: string) =>
    api.post<AuthResponse>('/api/auth/forgot-password', { email }),

  resetPassword: (email: string, codigo: string, nueva: string) =>
    api.post<AuthResponse>('/api/auth/reset-password', { email, codigo, nueva }),

  logout: () => api.post<{ ok: boolean }>('/api/auth/logout'),

  me: () => api.get<{ user: Usuario }>('/api/auth/me'),
}
