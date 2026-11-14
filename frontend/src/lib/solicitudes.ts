import { api } from './api'
import type { Solicitud, DashboardStats, ProgramacionDias, ProgramacionArea } from '@/types'

/* ============================================================
   Descargas de archivos.

   Todas pasan por descargar(). El motivo es concreto:

   /api/descargar REDIRIGE (303) a /login o /checkout cuando el usuario no
   tiene sesion o se acabaron sus descargas gratuitas. Con un <a href> o un
   window.open() esa redireccion se cumple en la pagina actual (o en una
   pestana nueva que queda vacia), y lo que se acaba guardando en disco es el
   HTML de /checkout renombrado como .xlsx.

   Descargando por fetch se puede distinguir la respuesta real de la
   redireccion: se mira el content-type y, si no es el del archivo, se avisa
   en vez de dejar un archivo roto en la carpeta del usuario.

   El <a download> con blob tampoco abre pestana ni navega, que es justo lo
   que se pidio.
   ============================================================ */

/**
 * Content-types con los que el servidor responde el archivo de verdad.
 *
 * Incluye `application/pdf` por los reportes de comandas, que usan el mismo
 * `descargar()`. Asi el manejo de la redireccion a /checkout y del 402 por
 * cuota agotada es uno solo, en vez de dos implementaciones parecidas.
 */
const TIPOS_ARCHIVO = /spreadsheet|excel|octet-stream|text\/csv|text\/plain|application\/pdf/

export type MotivoFallo =
  | 'sin-sesion'
  | 'sin-cuota'
  | 'sin-permiso'
  | 'sin-archivo'
  | 'error'

/**
 * `mensaje` es el texto que mando el backend (FastAPI lo pone en `detail`).
 *
 * Sin el, un 402 por cuota agotada y un 404 por "no hay datos" se veian igual:
 * "El archivo ya no esta disponible". Eso mandaba a buscar el problema al
 * lugar equivocado. El motivo sigue existiendo para los callers que quieran
 * decidir por tipo de fallo; el mensaje es para mostrarlo tal cual.
 */
export type ResultadoDescarga =
  | { ok: true }
  | { ok: false; motivo: MotivoFallo; mensaje?: string }

/** Saca el mensaje legible de un cuerpo de error de la API. */
function detalleDelError(cuerpo: unknown): string | undefined {
  if (!cuerpo || typeof cuerpo !== 'object') return undefined
  const obj = cuerpo as Record<string, unknown>
  for (const clave of ['detail', 'mensaje', 'error']) {
    const valor = obj[clave]
    if (typeof valor === 'string' && valor.trim()) return valor.trim()
  }
  return undefined
}

/**
 * Descarga una URL de la API sin abrir ventana ni cambiar de pagina.
 *
 * @param url        ruta del endpoint, por ejemplo `/api/descargar/folio.xlsx`
 * @param nombre     nombre con el que se guarda. Si se omite, lo pone el
 *                   servidor via Content-Disposition.
 */
export async function descargar(url: string, nombre?: string): Promise<ResultadoDescarga> {
  try {
    const res = await fetch(url, { credentials: 'include' })

    const contentDisposition = res.headers.get('content-disposition') ?? ''
    const contentType = res.headers.get('content-type') ?? ''
    // El 303 seguido por fetch deja res.redirected en true y la URL final ya
    // es /login o /checkout. El content-type pasa a ser text/html, que es lo
    // que delata que lo que bajo no es el archivo.
    const redirigido = res.redirected || /text\/html/i.test(contentType)
    const tipoOk = TIPOS_ARCHIVO.test(contentType)
    const destino = redirigido
      ? new URL(res.url, window.location.origin).pathname
      : ''

    // Redirecciones conocidas. Se miran por destino, no por "hubo un 303":
    // un proxy puede redirigir por otra razon y no queremos llamarlo cuota.
    if (destino.startsWith('/login')) return { ok: false, motivo: 'sin-sesion' }
    if (destino.startsWith('/checkout')) return { ok: false, motivo: 'sin-cuota' }

    if (!res.ok) {
      // FastAPI responde JSON con el motivo real (402 sin cuota, 403 rol,
      // 404 sin datos...). Antes se descartaba y todo caia en "sin-archivo".
      let mensaje: string | undefined
      try {
        mensaje = detalleDelError(await res.json())
      } catch {
        // 502/504 de un proxy no traen JSON: se queda el mensaje generico.
      }
      const motivo: MotivoFallo =
        res.status === 401
          ? 'sin-sesion'
          : res.status === 402
            ? 'sin-cuota'
            : res.status === 403
              ? 'sin-permiso'
              : res.status === 404
                ? 'sin-archivo'
                : 'error'
      return { ok: false, motivo, mensaje }
    }

    if (!tipoOk) return { ok: false, motivo: 'error' }

    // Nombre sugerido por el servidor, por si el que paso el caller no viene.
    let sugerido = nombre
    if (!sugerido) {
      const m = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(contentDisposition)
      if (m) sugerido = decodeURIComponent(m[1].trim())
    }
    if (!sugerido) {
      const par = new URL(res.url, window.location.origin).pathname.split('/').pop()
      sugerido = par || 'descarga'
    }

    const blob = await res.blob()
    const objectUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = objectUrl
    a.download = sugerido
    a.rel = 'noopener'
    document.body.appendChild(a)
    a.click()
    a.remove()
    // Sin revoke inmediato el navegador puede no haber tomado el blob todavia.
    setTimeout(() => URL.revokeObjectURL(objectUrl), 30_000)

    return { ok: true }
  } catch {
    return { ok: false, motivo: 'error' }
  }
}

/** Descarga el xlsx de una solicitud a la carpeta del usuario. */
export function descargarSolicitud(archivo: string): Promise<ResultadoDescarga> {
  return descargar(`/api/descargar/${encodeURIComponent(archivo)}`, archivo)
}

/** Descarga el log del dia. */
export function descargarLog(): Promise<ResultadoDescarga> {
  return descargar('/api/descargar-log')
}

/** Mensaje para mostrar al usuario segun el motivo del fallo. */
export function mensajeDescargaError(motivo: MotivoFallo, mensaje?: string): string {
  // El backend sabe mas que nosotros: si mando un texto, ese manda.
  if (mensaje && mensaje.trim()) return mensaje.trim()

  switch (motivo) {
    case 'sin-sesion':
      return 'Tu sesión expiró. Vuelve a iniciar sesión para descargar.'
    case 'sin-cuota':
      return 'No tenés descargas disponibles. Activa tu plan para seguir descargando.'
    case 'sin-permiso':
      return 'Tu rol no tiene permiso para descargar este archivo.'
    case 'sin-archivo':
      return 'El archivo ya no está disponible. Generá la solicitud de nuevo.'
    default:
      return 'No se pudo descargar. Intentá de nuevo en un momento.'
  }
}

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

  generarEntradas: (solicitudes: string[]) => {
    const formData = new FormData()
    for (const folio of solicitudes) formData.append('solicitudes', folio)
    return api.upload<{ ok: boolean; registros: number; archivo: string; download_url?: string }>(
      '/api/generar-entradas',
      formData,
    )
  },
}