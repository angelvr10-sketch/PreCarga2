import { api } from './api'
import type { BajaResult } from '@/types'

export const bajasApi = {
  list: () => api.get<BajaResult[]>('/api/bajas'),

  cargarBd: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.upload<{ ok: boolean; token: string; columnas: number }>('/api/cargar-bd', formData)
  },

  buscarBajas: (solicitudes: string[], bdToken: string) =>
    api.post<{ ok: boolean; encontrados: number; archivo: string }>('/api/buscar-bajas', {
      solicitudes,
      bd_token: bdToken,
    }),
}
