import {
  Toast,
  ToastAction,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from '@/components/ui/toast'
import { useToast } from '@/hooks/use-toast'

/**
 * Renderiza todos los toasts activos.
 *
 * Va junto a <ToastProvider> en la raiz de la app: si el provider
 * faltara, Radix lanza un error al intentar abrir un toast.
 */
export function Toaster() {
  const toasts = useToast()

  return (
    <ToastProvider swipeDirection='right' duration={5000}>
      {toasts.map((t) => (
        <Toast
          key={t.id}
          variant={t.variant}
          open={t.abierto}
          onOpenChange={(abierto: boolean) => {
            if (!abierto) t.cerrar()
          }}
          // duracion null = el toast espera a que el usuario lo cierre.
          duration={t.duracion === null ? Infinity : (t.duracion ?? 5000)}
        >
          <div className='flex-1 space-y-1'>
            <ToastTitle>{t.titulo}</ToastTitle>
            {t.descripcion && <ToastDescription>{t.descripcion}</ToastDescription>}
          </div>
          {t.accion && (
            // altText (y no alt) es la prop que esta version de Radix exige
            // para el nombre accesible del boton de accion.
            <ToastAction altText={t.accion.etiqueta} onClick={t.accion.alPulsar}>
              {t.accion.etiqueta}
            </ToastAction>
          )}
          <ToastClose />
        </Toast>
      ))}
      <ToastViewport />
    </ToastProvider>
  )
}
