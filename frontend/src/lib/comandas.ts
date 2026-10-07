/**
 * Cliente de /api/comandas.
 *
 * Va sobre el `api` de lib/api.ts, que ya resuelve `credentials: 'include'`,
 * los timeouts y el `ApiError` con mensaje en español. Por eso las descargas
 * de PDF van por `descargar()` de lib/solicitudes.ts y no por un <a href>.
 *
 * POR QUE LAS DESCARGAS NO SON UN <a href> NORMAL:
 * los endpoints de reporte responden 402 con un JSON cuando el usuario se
 * quedo sin cuota. Con un <a href> el navegador NAVEGARIA a ese JSON y la
 * pestana quedaria mostrando texto crudo en vez de descargar un archivo.
 * `descargar()` lo distingue y devuelve el motivo, que `mensajeDescargaError()`
 * traduce a un mensaje que el usuario entiende.
 */
import { api } from './api'
import { descargar, type ResultadoDescarga } from './solicitudes'
import type {
  ComandasDeFecha,
  Diagnostico,
  Estadisticas,
  FechasComandas,
  ResultadoImportar,
  SerieComandas,
  TipoReporte,
} from '@/types/comandas'

/** Los endpoints de reporte aceptan estos tipos; uno mas seria un 404. */
const TIPOS_REPORTE: TipoReporte[] = ['estadistico', 'todas', 'mortera', 'vales']

function qs(params: Record<string, string | undefined>): string {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v) p.set(k, v)
  }
  const s = p.toString()
  return s ? `?${s}` : ''
}

export const comandasApi = {
  /** Fechas con comandas del usuario en sesion, de mas reciente a mas vieja. */
  fechas: () => api.get<FechasComandas>('/api/comandas/fechas'),

  /** Comandas de una fecha. Sin `fecha` el backend usa hoy. */
  listar: (fecha?: string) =>
    api.get<ComandasDeFecha>(`/api/comandas/${qs({ fecha })}`),

  /** Agregaciones del dashboard, ya sumadas en el servidor. */
  estadisticas: (fecha?: string) =>
    api.get<Estadisticas>(`/api/comandas/estadisticas${qs({ fecha })}`),

  /**
   * Serie diaria de comandas por barco, de todos los usuarios.
   *
   * Es la unica llamada de este cliente que NO va por las comandas del usuario en
   * sesion: alimenta una tarjeta y una grafica del dashboard, donde las demas
   * cifras ya son globales. El backend solo devuelve conteos por fecha y barco.
   */
  serie: (dias: number) => api.get<SerieComandas>(`/api/comandas/serie${qs({ dias: String(dias) })}`),

  /**
   * Sube un reporte. Usa `api.upload`, que tiene timeout de 180 s (el de
   * `api.get` son 30 s y un reporte grande no cabe).
   */
  importar: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.upload<ResultadoImportar>('/api/comandas/importar', formData)
  },

  /** Conteos de la base. Solo responde a admin. */
  diagnostico: () => api.get<Diagnostico>('/api/comandas/diagnostico'),
}

/** La URL del reporte, para enlazarla o pasarla a descargar(). */
export function urlReporte(tipo: TipoReporte, fecha: string): string {
  if (!TIPOS_REPORTE.includes(tipo)) {
    // programming error, no entrada del usuario: falla en desarrollo, no en
    // produccion con un 404 dificil de entender.
    throw new Error(`Tipo de reporte desconocido: ${tipo}`)
  }
  return `/api/comandas/reporte/${tipo}${qs({ fecha })}`
}

/** La URL del PDF de una comanda suelta. */
export function urlComanda(folio: string, fecha: string): string {
  return `/api/comandas/reporte/comanda/${encodeURIComponent(folio)}${qs({ fecha })}`
}

/**
 * Descarga un reporte de comandas.
 *
 * No cuelga: si el usuario se quedo sin cuota, `descargar()` devuelve
 * `{ ok: false }` y el toast lo explica. Cada descarga exitosa descuenta una del
 * contador del backend, asi que hay que deshabilitar el boton mientras corre.
 */
export function descargarReporte(tipo: TipoReporte, fecha: string): Promise<ResultadoDescarga> {
  return descargar(urlReporte(tipo, fecha))
}

/** Descarga el PDF de una comanda individual. */
export function descargarComanda(folio: string, fecha: string): Promise<ResultadoDescarga> {
  return descargar(urlComanda(folio, fecha))
}

/* ── Formato ─────────────────────────────────────────────────── */

/**
 * La fecha de hoy en ISO local, 'YYYY-MM-DD'.
 *
 * Se arma a mano en vez de usar `toISOString()` porque ese convierte a UTC: en
 * Mexico (UTC-6) a las 20:00 del dia 6 devolveria '2026-10-07', la fecha del
 * dia siguiente. Para agrupar comandas por dia de operacion eso seria un
 * error fantasma que solo aparece de noche.
 */
export function hoyIso(): string {
  const d = new Date()
  const mes = String(d.getMonth() + 1).padStart(2, '0')
  const dia = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mes}-${dia}`
}

/** '2026-10-07' -> '07/10/2026'. Para lo que se ve en pantalla. */
export function fechaCorta(iso: string): string {
  const [a, m, d] = iso.split('-')
  return d && m && a ? `${d}/${m}/${a}` : iso
}

/** '2026-10-07' -> 'miércoles, 7 de octubre de 2026'. */
export function fechaLarga(iso: string): string {
  const d = new Date(`${iso}T12:00:00`)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('es-MX', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

/**
 * El día de la semana en mayúsculas, como lo escribe el machote.
 *
 * Sale de `toLocaleDateString` con el locale 'es-MX'. El texto del PDF va con
 * acento ('MIÉRCOLES') y el papel firmado lo lleva, asi que aqui tambien: si
 * se normalizara a 'MIERCOLES', la pantalla y el PDF dirian cosas distintas
 * para el mismo día.
 */
export function diaSemana(iso: string): string {
  const d = new Date(`${iso}T12:00:00`)
  if (Number.isNaN(d.getTime())) return ''
  const dia = d.toLocaleDateString('es-MX', { weekday: 'long' })
  return dia.charAt(0).toUpperCase() + dia.slice(1)
}

/**
 * Une un registro con su PAX para las tablas.
 *
 * Es lo que hacen las dos tablas de la izquierda del dashboard: "Pax por
 * destino" y "Pax por compania", ordenadas de mayor a menor.
 */
export function aFilas(
  conteo: Record<string, number>,
): Array<{ nombre: string; pax: number }> {
  return Object.entries(conteo)
    .map(([nombre, pax]) => ({ nombre, pax }))
    .sort((a, b) => b.pax - a.pax)
}
