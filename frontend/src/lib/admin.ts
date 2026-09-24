import { api } from './api'
import type { LogEntry, Usuario } from '@/types'

export const adminApi = {
  listUsers: () => api.get<Usuario[]>('/api/admin/usuarios'),

  updateUser: (id: string, data: Partial<Usuario>) =>
    api.patch<Usuario>(`/api/admin/usuarios/${id}`, data),

  getLogs: () => api.get<{ fecha: string; contenido: string }>('/api/logs'),
}
