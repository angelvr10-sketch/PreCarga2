/**
 * Tipos del modulo de comandas.
 *
 * Reflejan lo que devuelve `core/comandas/parser.py` y `core/comandas/stats.py`.
 *
 * OJO con `menu_1`: el backend SIEMPRE lo pone igual a `pax`, aunque la columna
 * "MENU 1" del PDF diga otra cosa. Hay comandas reales donde difieren (JUL026:
 * pax 125, menu1 126). Ver test_fixtures_reales.py. Por eso `total_pax` se
 * calcula como `menu_1 + menu_2` y no sumando la columna `pax`.
 */

export type TipoComanda = 'MORTERA' | 'VIANDA'

/** Los cinco modos de transporte que el parser reconoce. */
export type Transporte = 'AEREO' | 'GANGWAY' | 'MARÍTIMO' | 'VIUDA' | 'CANASTILLA'

export interface Comanda {
  /** Folio, ej. 'OCT001'. Tres letras y tres digitos en los reportes reales. */
  comanda: string
  /** 'HH:MM', sin segundos. */
  horario: string
  compania: string
  destino: string
  /** Personas. */
  pax: number
  transporte: string
  /** Siempre igual a `pax` (ver nota arriba). */
  menu_1: number
  menu_2: number
  tipo: TipoComanda
  /** Texto de la columna CUSTODIO del reporte. */
  observaciones: string
}

/** Respuesta de GET /api/comandas/ */
export interface ComandasDeFecha {
  fecha: string
  comandas: Comanda[]
  total: number
  total_pax: number
  /** 'REFORMA PEMEX' o 'CERRO DE LA PEZ'. */
  titulo: string
}

/** Respuesta de GET /api/comandas/estadisticas */
export interface Estadisticas {
  fecha: string
  total_comandas: number
  total_alimentos: number
  total_menu1: number
  total_menu2: number
  total_mortera: number
  total_viandas: number
  /** Clave larga: 'PAPA LOAPAN (GANGWAY)'. Para la tabla. */
  por_destino: Record<string, number>
  /** Clave corta: 'PAPA LOAPAN (G)'. Para la leyenda del donut. */
  por_destino_grafico: Record<string, number>
  por_compania: Record<string, number>
  por_transporte: Record<string, number>
}

/** Respuesta de GET /api/comandas/fechas */
export interface FechasComandas {
  fechas: string[]
  hoy: string
}

/**
 * Respuesta de GET /api/comandas/serie
 *
 * Serie diaria de comandas por barco, de TODOS los usuarios: alimenta la
 * tarjeta y la grafica del dashboard, donde lo demas ya es global.
 *
 * OJO con `sin_asignar`: la tabla `comandas` no tiene columna de barco, asi que
 * el backend lo deduce de quien subio la comanda (ver `BARCO_POR_USUARIO` en
 * core/comandas/serie.py). Las comandas de un usuario que no este en ese mapa no
 * se descartan: se cuentan aqui para que el frontend avise, en vez de
 * desaparecer del grafico como si fueran un dia sin actividad.
 */
export interface SerieComandas {
  /** Fechas de la ventana, en orden: mas viejo -> hoy. */
  dias: string[]
  /** Comandas por dia de RPX. */
  rpx: number[]
  /** Comandas por dia de CPZ. */
  cpz: number[]
  /** Total (no diario) de comandas de la ventana sin barco asignado. */
  sin_asignar: number
  /** Total de comandas de la ventana, sin filtrar por barco. */
  total: number
}

/** Respuesta de POST /api/comandas/importar */
export interface ResultadoImportar {
  ok: boolean
  fecha: string
  fecha_texto: string
  titulo: string
  guardadas: number
  folios: string[]
  total: number
  total_pax: number
  morteras: number
  /** Folios citados en el PDF que no se interpretaron, y avisos de fecha. */
  advertencias: string[]
  /** Texto listo para el toast. */
  mensaje: string
}

/** Los cuatro reportes en bloque mas el PDF individual. */
export type TipoReporte = 'estadistico' | 'todas' | 'mortera' | 'vales'

export interface Diagnostico {
  usuario: string
  comandas_en_tabla: number
  mis_comandas: number
  mis_fechas: number
  ultimas_fechas: string[]
  error: string | null
}
