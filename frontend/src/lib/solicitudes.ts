import { api } from './api'
import type { Solicitud, DashboardStats, ProgramacionDias, ProgramacionArea } from '@/types'

export const solicitudesApi = {
  list: (page = 1, search = '') =>
    api.get<{ solicitudes: Solicitud[]; total: number; page: number; total_pages: number }>(
      `/api/solicitudes?page=${page}&search=${encodeURIComponent(search)}`,
    ),

  get: (id: number) => api.get<Solicitud>(`/api/solicitudes/${id}`),

  dashboard: () => api.get<DashboardStats>('/api/dashboard/stats'),

  programacionDias: (dias = 14) => api.get<ProgramacionDias>(`/api/dashboard/programacion-dias?dias=${dias}`),

  programacionArea: (dias = 14, barco = '') =>
    api.get<ProgramacionArea>(
      `/api/dashboard/programacion-area?dias=${dias}${barco ? `&barco=${encodeURIComponent(barco)}` : ''}`,
    ),

  procesarPdf: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.upload<{ ok: boolean; mensaje: string; archivo: string }>('/api/procesar-pdf', formData)
  },

  /**
   * Descarga el xlsx de una solicitud a la carpeta del usuario.
   *
   * No se usa un <a href> porque /api/descargar REDIRIGE (303) a /checkout o
   * /login cuando no hay permiso, y con fetch la redireccion se sigue en
   * silencio: llegaria HTML y el navegador guardaria un archivo roto en vez de
   * avisar. Por eso se valida el content-type antes de guardar nada.
   */
  descargarSolicitud: async (archivo: string): Promise<void> => {
    const res = await fetch(`/api/descargar/${encodeURIComponent(archivo)}`, {
      credentials: 'include',
    })
    const type = res.headers.get('content-type') ?? ''
    if (!/spreadsheet|excel|octet-stream/.test(type)) {
      throw new Error('No se pudo descargar (revisa tus descargas disponibles)')
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = archivo
    document.body.appendChild(a)
    a.click()
    a.remove()
    // Sin revoke inmediato el navegador puede no haber tomado el blob.
    setTimeout(() => URL.revokeObjectURL(url), 30_000)
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
