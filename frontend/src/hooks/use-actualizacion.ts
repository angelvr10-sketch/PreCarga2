import { useEffect } from 'react'
import { toast } from './use-toast'

/* ============================================================
   Aviso de version nueva.

   El service worker descarga el sw.js nuevo por su cuenta (el
   navegador lo comprueba en cada carga). Cuando esa version queda
   esperando, este hook lo avisa y ofrece recargar.

   Por que NO se recarga solo: el usuario puede estar a mitad de un
   formulario o esperando que termine una subida. Perder eso por un
   refresco automatico es peor que esperar unos segundos.
   ============================================================ */

/** Cada cuanto se busca una version nueva con la app abierta. */
const INTERVALO_MS = 60 * 60 * 1000 // 1 hora

/**
   Debe coincidir con el mensaje que escucha sw.js. Si cambia un
   lado, el refresh se queda colgado sin avisar.
   */
const MENSAJE_SKIP_WAITING = 'skip-waiting'

export function useActualizacion() {
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return
    // En desarrollo no hay SW registrado: este codigo solo generaria
    // falsos positivos.
    if (!import.meta.env.PROD) return

    let registro: ServiceWorkerRegistration | undefined
    /**
     * Worker ya anunciado. Guarda el objeto y no un booleano para que una
     * version posterior pueda volver a avisar: si el usuario recarga y llega
     * otro despliegue, ese worker nuevo no es el mismo y hay que avisarlo.
     */
    let anunciado: ServiceWorker | null = null
    /** Pasa a true solo si el usuario pulso Recargar. */
    let recargando = false

    const activar = () => {
      // controllerchange dispara de nuevo al tomar el control el SW
      // nuevo, y recargar otra vez entraria en bucle. De ahi la
      // bandera: el segundo reload no se vuelve a pedir.
      if (recargando) return
      recargando = true
      registro?.waiting?.postMessage(MENSAJE_SKIP_WAITING)
      // Si el SW no llega a tomar el control, recargar igual: la
      // navegacion es network-first, asi que el index.html que llegue
      // es el nuevo y la app funciona de la misma manera.
      setTimeout(() => window.location.reload(), 800)
    }

    const preguntar = () => {
      if (!registro) return
      // Sin controller no hay version anterior: es la primera
      // instalacion y no hay nada que actualizar.
      if (!registro.waiting || !navigator.serviceWorker.controller) return
      if (anunciado === registro.waiting) return

      anunciado = registro.waiting
      toast({
        titulo: 'Hay una version nueva disponible',
        descripcion: 'Recarga para obtener los \u00faltimos cambios.',
        variant: 'aviso',
        // No se cierra solo: es una decision del usuario, no un aviso
        // que pueda expirar mientras esta haciendo otra cosa.
        duracion: null,
        accion: {
          etiqueta: 'Recargar',
          alPulsar: activar,
        },
      })
    }

    /**
     * updatefound es el aviso de que el navegador empezo a instalar un sw.js
     * distinto al que estaba activo.
     *
     * Sin este listener el hook solo miraba registration.waiting al montar,
     * asi que un despliegue que ocurre con la app abierta se perdia entero:
     * el aviso no aparecia hasta la siguiente recarga de la pagina. Es justo
     * el caso que un aviso de version nueva debe cubrir.
     */
    const alEncontrarUpdate = () => {
      const entrante = registro?.installing
      if (!entrante) return
      // Cada cambio de estado se revisa: el worker pasa por installing antes
      // de quedarse esperando.
      entrante.addEventListener('statechange', preguntar)
    }

    const alCambiarControl = () => {
      // controllerchange se dispara cada vez que el control cambia,
      // incluida la primera activacion. Solo recargamos si veniamos
      // de un aviso, que es lo unico que marca `recargando`.
      if (recargando) window.location.reload()
    }

    navigator.serviceWorker.addEventListener('controllerchange', alCambiarControl)

    // El registro puede no existir aun en el primer mount (la pagina
    // acaba de cargar y el registro espera al evento load), asi que se
    // consulta y, si no aparece, se reintenta un rato.
    const intentar = () => {
      if (registro) return
      navigator.serviceWorker
        .getRegistration()
        .then((r) => {
          if (!r || registro) return
          registro = r
          registro.addEventListener('updatefound', alEncontrarUpdate)
          preguntar()
        })
        .catch(() => {})
    }
    intentar()
    const reintento = setInterval(() => {
      if (registro) {
        clearInterval(reintento)
        return
      }
      intentar()
    }, 2000)

    // Busca activamente: con la app abierta horas, el navegador no
    // vuelve a pedir el sw.js hasta la siguiente carga.
    const buscar = () => registro?.update().catch(() => {})
    const periodo = setInterval(buscar, INTERVALO_MS)

    // Al volver a la pestana es el momento natural de comprobarlo.
    const alVolver = () => {
      if (document.visibilityState === 'visible') buscar()
    }
    document.addEventListener('visibilitychange', alVolver)

    return () => {
      clearInterval(reintento)
      clearInterval(periodo)
      registro?.removeEventListener('updatefound', alEncontrarUpdate)
      document.removeEventListener('visibilitychange', alVolver)
      navigator.serviceWorker.removeEventListener('controllerchange', alCambiarControl)
    }
  }, [])
}
