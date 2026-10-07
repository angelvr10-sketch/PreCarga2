export interface Usuario {
  id: string
  nombre: string
  email: string
  admin: boolean
  /**
   * Rol crudo: 'admin' | 'usuario' | 'lector'.
   *
   * Hace falta aparte de `admin` porque el rol 'usuario' NO es lector. Con solo
   * el booleano no hay forma de distinguirlos, y tratar a los usuarios normales
   * como lectores los deja sin los reportes que si les tocan. Lo consume el
   * modulo de comandas; el resto de la app usa `admin`.
   */
  rol: string
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
  total_movimientos: number
  altas_generadas: number
  bajas_procesadas: number
  total_companias: number
  /**
   * Comandas de alimentos de los dos barcos, de todos los usuarios y de todo el
   * historico. Global, como las demas cifras de esta tarjeta.
   *
   * Es de todo el historico, no del periodo del selector de arriba: la tarjeta
   * es un acumulado, como las otras cinco.
   */
  total_comandas: number
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
