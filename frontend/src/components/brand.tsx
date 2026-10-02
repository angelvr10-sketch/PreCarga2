import { cn } from '@/lib/utils'

/**
 * Assets de marca. Viven en /public y se referencian por ruta absoluta
 * para que el navegador las cachee y no pasen por el chunk de Vite.
 *
 *  - logo_precarga.png      lockup completo (marca "P" + wordmark), 384px
 *  - logo_precarga_mark.png solo la marca "P", 128px
 *
 * Ambos tienen canal alfa y conservan la proporcion real del original
 * (mark ~1.16:1, mas ancho que alto). Por eso se dimensionan con `h-*`
 * y `w-auto`: poner `w-* h-*` simultaneo los deformaria.
 *
 * Nota: el wordmark "Pre" es blanco, asi que el lockup completo solo
 * funciona sobre superficies oscuras. Para fondos claros usar <BrandMark />.
 */
const LOCKUP_SRC = '/logo_precarga.png'
const MARK_SRC = '/logo_precarga_mark.png'

interface BrandProps {
  className?: string
  alt?: string
}

/**
 * Lockup completo para headers y hero. Incluye el wordmark, asi que no
 * hay que acompanarlo de texto "PreCarga" al lado.
 */
export function BrandLockup({ className, alt = 'PreCarga' }: BrandProps) {
  return (
    <img
      src={LOCKUP_SRC}
      alt={alt}
      draggable={false}
      className={cn('h-9 w-auto shrink-0 select-none', className)}
    />
  )
}

/**
 * Solo la marca "P". Para slots pequenos (sidebar, cabeceras de card) o
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
