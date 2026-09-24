export interface Usuario {
  id: string
  nombre: string
  email: string
  admin: boolean
  verificado: boolean
  created_at: string
}

export interface Solicitud {
  id: number
  folio: string
  tipo: string
  estatus: string
  created_at: string
  personal_count?: number
  bajas_count?: number
  compania?: string
  destino?: string
}

export interface Personal {
  id: number
  nombre: string
  rfc: string
  solicitud_id: number
}

export interface Compania {
  id: string
  razon_social: string
  nombre_corto: string
}

export interface Activo {
  id: string
  nombre: string
}

export interface LogEntry {
  timestamp: string
  usuario: string
  accion: string
  detalle: string
}

export interface DashboardStats {
  total_solicitudes: number
  total_personal: number
  solicitudes_hoy: number
  altas_generadas: number
  bajas_procesadas: number
  total_companias: number
}

export interface BajaResult {
  nombre: string
  rfc: string
  ubicacion: string
}

export interface ProgramacionDias {
  dias: string[]
  rpx: number[]
  cpz: number[]
}

export interface ProgramacionArea {
  dias: string[]
  barcos: string[]
  rpx: { altas: number[]; bajas: number[] }
  cpz: { altas: number[]; bajas: number[] }
}
