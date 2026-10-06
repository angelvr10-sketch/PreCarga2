import { useEffect, useState } from 'react'

export type ToastVariant = 'default' | 'exito' | 'error' | 'aviso'

export interface ToastData {
  titulo: string
  descripcion?: string
  variant?: ToastVariant
  /** Etiqueta del boton de accion. Sin esto, el toast no lleva boton. */
  accion?: { etiqueta: string; alPulsar: () => void }
  /** null = no se cierra solo (avisos que exigen una decision). */
  duracion?: number | null
}

interface Toast extends ToastData {
  id: number
  abierto: boolean
  /** Cierra este toast con animacion. Lo usa el Toaster al cerrarse. */
  cerrar: () => void
}

/* ============================================================
   Store de toasts, fuera de React.

   Vive en un modulo y no en un Context a proposito: el aviso de
   version nueva lo dispara el listener del service worker, que
   corre fuera del arbol de React. Con un Context, ese codigo
   necesitaria un provider debajo para poder llamarlo.

   useSyncExternalStore es lo correcto para esto: React lee el
   estado sin que haga falta duplicarlo en useState.
   ============================================================ */

/** Cuantos toasts se ven a la vez. Mas que eso tapa la pantalla. */
const LIMITE = 3
/** Margen para que se vea la animacion de salida antes de borrar. */
const RETARDO_SALIDA = 220

let secuencia = 0
let toasts: Toast[] = []
const oyentes = new Set<() => void>()

const avisar = () => {
  for (const o of oyentes) o()
}

const emitir = (siguiente: Toast[]) => {
  toasts = siguiente
  avisar()
}

/**
 * Muestra un toast y devuelve las funciones para controlarlo.
 *
 * El id se genera antes de nada porque el llamador puede querer
 * cerrar el toast recien creado (tipico: mostrar un error y
 * desaparecerlo si la operacion luego funciona).
 */
export function toast(datos: ToastData) {
  const id = ++secuencia
  // cerrar se referencia por id y no por el objeto: asi sigue siendo
  // valido aunque el toast se vuelva a crear al actualizarlo.
  const nuevo: Toast = { ...datos, id, abierto: true, cerrar: () => descartar(id) }

  emitir([...toasts, nuevo].slice(-LIMITE))

  if (datos.duracion !== null) {
    const ms = datos.duracion ?? 5000
    setTimeout(() => descartar(id), ms)
  }

  return {
    id,
    cerrar: () => descartar(id),
    /** Cambia el texto o la variante con el toast ya en pantalla. */
    actualizar: (parche: Partial<ToastData>) => {
      emitir(
        toasts.map((t) => (t.id === id ? { ...t, ...parche } : t)),
      )
    },
  }
}

/** Cierra con animacion y borra un instante despues. */
function descartar(id: number) {
  emitir(toasts.map((t) => (t.id === id ? { ...t, abierto: false } : t)))
  setTimeout(() => emitir(toasts.filter((t) => t.id !== id)), RETARDO_SALIDA)
}

export function useToast() {
  const [, forzar] = useState(0)

  useEffect(() => {
    const o = () => forzar((n) => n + 1)
    oyentes.add(o)
    return () => {
      oyentes.delete(o)
    }
  }, [])

  return toasts
}

/**
 * Atajo para mostrar mensajes de una vez, sin conservar el id.
 *
 * Pensado para el 90% de los casos: errores de red y confirmaciones
 * simples, donde nadie va a necesitar cerrar el toast a mano.
 */
export function notificar(
  titulo: string,
  descripcion?: string,
  variant: ToastVariant = 'default',
) {
  toast({ titulo, descripcion, variant })
}
