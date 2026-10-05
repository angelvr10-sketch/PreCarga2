import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Convierte una fecha de la API a un Date LOCAL.
 *
 * Las fechas de llegada llegan como "YYYY-MM-DD" (solo fecha). Si se
 * construye con new Date("YYYY-MM-DD"), el navegador la interpreta como
 * medianoche UTC y, en el hemisferio negativo (America), la traslada al dia
 * anterior al formatearla. Por eso se construye la Date a partir de las
 * partes año/mes/dia, que sí se interpretan como hora local.
 *
 * Los datetimes con hora se parsean tal cual: con "T" y sin "Z" son locales,
 * con "Z"/"+00:00" el offset de zona ya viene determinado.
 */
export function fechaLocal(s: string | null | undefined): Date | null {
  if (!s) return null
  const raw = String(s).trim()
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
    const [y, m, d] = raw.split('-').map(Number)
    return new Date(y, m - 1, d)
  }
  const d = new Date(raw)
  return isNaN(d.getTime()) ? null : d
}

export function formatFecha(s: string | null | undefined): string {
  const d = fechaLocal(s)
  return d ? d.toLocaleDateString() : ''
}
