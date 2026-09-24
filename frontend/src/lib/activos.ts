import { api } from './api'
import type { Activo } from '@/types'

export const activosApi = {
  list: () => api.get<Activo[]>('/api/activos'),

  create: (nombre: string) =>
    api.post<Activo>('/api/activos', { nombre }),

  delete: (nombre: string) =>
    api.delete<{ ok: boolean }>(`/api/activos/${encodeURIComponent(nombre)}`),
}
