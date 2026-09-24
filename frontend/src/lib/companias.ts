import { api } from './api'
import type { Compania } from '@/types'

export const companiasApi = {
  list: () => api.get<Compania[]>('/api/companias'),

  create: (razonSocial: string, nombreCorto: string) =>
    api.post<Compania>('/api/companias', { razon_social: razonSocial, nombre_corto: nombreCorto }),

  delete: (razonSocial: string) =>
    api.delete<{ ok: boolean }>(`/api/companias/${encodeURIComponent(razonSocial)}`),
}
