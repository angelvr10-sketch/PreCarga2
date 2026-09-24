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

  logout: () => api.post<{ ok: boolean }>('/api/auth/logout'),

  me: () => api.get<{ user: Usuario }>('/api/auth/me'),
}
