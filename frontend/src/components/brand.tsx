import { cn } from '@/lib/utils'

/**
 * Assets de marca. Viven en /public y se referencian por ruta absoluta
 * para que el navegador las cachee y no pasen por el chunk de Vite.
 *
 * Paquete original en /logos (fuente maestra, no se sirve). Copias en
 * /public/logos:
 *
 *  - precarga-horizontal-dark.svg   lockup completo, 410x108 (ratio 3.8)
 *  - precarga-vertical-dark.svg     lockup apilado, 334x268
 *  - precarga-icono.svg             solo la marca, 212x154
 *  - *_light.svg                    iguales pero con el texto en oscuro, para
 *                                   superficies claras (la app es dark-only,
 *                                   asi que hoy no se usan)
 *
 * Se usan los SVG y no los PNG: escalan sin perder calidad y pesan menos
 * (12 KB contra 122 KB del PNG equivalente). Ademas el wordmark viene como
 * trazados, no como texto, asi que no depende de la fuente instalada.
 *
 * Nota: las variantes 'dark' son las de fondo oscuro (wordmark en blanco).
 * El tema de la app es dark-only, asi que todos los usos van con 'dark'.
 */
const LOCKUP_SRC = '/logos/precarga-horizontal-dark.svg'
const MARK_SRC = '/logos/precarga-icono.svg'

/** Proporcion real del lockup horizontal, para reserva el espacio correcto. */
const RATIO_LOCKUP = 3.796

interface BrandProps {
  className?: string
  alt?: string
}

/**
 * Lockup horizontal para headers y hero. Incluye el wordmark, asi que no
 * hay que acompanarlo de texto "PreCarga" al lado.
 */
export function BrandLockup({ className, alt = 'PreCarga Operaciones Marítimas' }: BrandProps) {
  return (
    <img
      src={LOCKUP_SRC}
      alt={alt}
      draggable={false}
      style={{ aspectRatio: RATIO_LOCKUP }}
      className={cn('h-9 w-auto shrink-0 select-none', className)}
    />
  )
}

/**
 * Solo la marca. Para slots pequenos (sidebar, cabeceras de card) o
 * cuando el wordmark ya esta en texto al lado.
 */
export function BrandMark({ className, alt = 'PreCarga' }: BrandProps) {
  return (
    <img
      src={MARK_SRC}
      alt={alt}
      draggable={false}
      className={cn('h-6 w-auto shrink-0 select-none', className)}
    />
  )
}