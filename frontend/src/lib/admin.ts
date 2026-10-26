import { api } from './api'
import type { Usuario } from '@/types'

export type Rol = 'admin' | 'usuario' | 'lector'

export interface AdminUser extends Usuario {
  rol: Rol
  activo: boolean
  expira: string | null
  descargas_usadas: number
}

export interface CrearUsuarioPayload {
  nombre: string
  email: string
  password: string
  rol: Rol
  dias?: number
}

export interface ActualizarUsuarioPayload {
  rol?: Rol
  activo?: boolean
  verificado?: boolean
  password?: string
  dias?: number
}

export const adminApi = {
  listUsers: () => api.get<AdminUser[]>('/api/admin/usuarios'),

  createUser: (data: CrearUsuarioPayload) =>
    api.post<{ ok: boolean; mensaje?: string }>('/api/admin/usuarios', data),

  updateUser: (id: string, data: ActualizarUsuarioPayload) =>
    api.patch<{ ok: boolean }>(`/api/admin/usuarios/${id}`, data),

  deleteUser: (id: string) =>
    api.delete<{ ok: boolean }>(`/api/admin/usuarios/${id}`),

  getLogs: () => api.get<{ fecha: string; contenido: string }>('/api/logs'),
}
