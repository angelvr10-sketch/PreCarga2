import { api } from './api'
import type { BajaResult } from '@/types'

export const bajasApi = {
  list: () => api.get<BajaResult[]>('/api/bajas'),

  cargarBd: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.upload<{ ok: boolean; token: string; columnas: number }>('/api/cargar-bd', formData)
  },

  // Este endpoint declara `Form(...)` en el backend (multipart), no JSON.
  // Enviandolo con api.post + objeto, FastAPI no encontraba los campos y
  // respondia 422 con dos "Field required" (solicitudes y bd_token).
  // `solicitudes` es una lista: FormData la lleva como campos repetidos,
  // igual que hace generarEntradas con generar-entradas.
  buscarBajas: (solicitudes: string[], bdToken: string) => {
    const formData = new FormData()
    for (const folio of solicitudes) formData.append('solicitudes', folio)
    formData.append('bd_token', bdToken)
    // `mensaje` solo viene cuando ok:false (el backend responde HTTP 200 con el
// motivo en el cuerpo, no con un 4xx), por eso es opcional.
    return api.upload<{
      ok: boolean
      encontrados?: number
      archivo?: string
      mensaje?: string
    }>('/api/buscar-bajas', formData)
  },
}
