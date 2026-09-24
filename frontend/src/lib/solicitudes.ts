import { api } from './api'
import type { Solicitud, DashboardStats, ProgramacionDias, ProgramacionArea } from '@/types'

export const solicitudesApi = {
  list: (page = 1, search = '') =>
    api.get<{ solicitudes: Solicitud[]; total: number; page: number; total_pages: number }>(
      `/api/solicitudes?page=${page}&search=${encodeURIComponent(search)}`,
    ),

  get: (id: number) => api.get<Solicitud>(`/api/solicitudes/${id}`),

  dashboard: () => api.get<DashboardStats>('/api/dashboard/stats'),

  programacionDias: () => api.get<ProgramacionDias>('/api/dashboard/programacion-dias'),

  programacionArea: (barco = '') =>
    api.get<ProgramacionArea>(
      `/api/dashboard/programacion-area${barco ? `?barco=${encodeURIComponent(barco)}` : ''}`,
    ),

  procesarPdf: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.upload<{ ok: boolean; mensaje: string }>('/api/procesar-pdf', formData)
  },

  generarEntradas: (solicitudes: string[]) => {
    const formData = new FormData()
    for (const folio of solicitudes) formData.append('solicitudes', folio)
    return api.upload<{ ok: boolean; registros: number; archivo: string; download_url?: string }>(
      '/api/generar-entradas',
      formData,
    )
  },
}
