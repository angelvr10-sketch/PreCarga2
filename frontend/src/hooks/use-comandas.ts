/**
 * Hooks de TanStack Query para comandas.
 *
 * Las claves son jerarquicas para poder invalidar por prefijo:
 *
 *   ['comandas', 'fechas']           -> todas las fechas del usuario
 *   ['comandas', 'lista',  fecha]    -> comandas de un dia
 *   ['comandas', 'stats',  fecha]    -> agregaciones de un dia
 *
 * Tras importar un reporte hay que invalidar las tres: la fecha nueva puede no
 * existir en la lista de fechas, y las comandas y agregaciones de ese dia
 * cambiaron. `queryClient.invalidateQueries({ queryKey: ['comandas'] })` las
 * cubre de una vez.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { comandasApi, hoyIso } from '@/lib/comandas'
import type { TipoReporte } from '@/types/comandas'

/** Fechas con datos del usuario. */
export function useFechas() {
  return useQuery({
    queryKey: ['comandas', 'fechas'],
    queryFn: async () => {
      const res = await comandasApi.fechas()
      return res.fechas
    },
    // Las fechas cambian solo al importar un reporte, y eso invalida la cache
    // explicitamente. Un minuto es mas que suficiente.
    staleTime: 60_000,
  })
}

/** Comandas de una fecha. Sin fecha, usa la de hoy. */
export function useComandas(fecha: string | undefined) {
  return useQuery({
    queryKey: ['comandas', 'lista', fecha ?? 'hoy'],
    queryFn: () => comandasApi.listar(fecha),
    enabled: !!fecha,
    staleTime: 60_000,
  })
}

/**
 * Agregaciones del dashboard.
 *
 * Es una consulta aparte y no un `useMemo` sobre las comandas, a proposito: el
 * backend ya sabe sumarlas, y mandar el conteo completo por la red para
 * recalcularlo en el navegador es tirar el calculo. Tambien permite que el
 * grafico aparezca sin esperar a toda la tabla.
 */
export function useEstadisticas(fecha: string | undefined) {
  return useQuery({
    queryKey: ['comandas', 'stats', fecha ?? 'hoy'],
    queryFn: () => comandasApi.estadisticas(fecha),
    enabled: !!fecha,
    staleTime: 60_000,
  })
}

/**
 * Sube un reporte.
 *
 * `onSuccess` invalida todo lo de comandas, asi que la pantalla se actualiza
 * sola sin que la pagina tenga que recargar nada a mano.
 */
export function useImportar() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => comandasApi.importar(file),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['comandas'] })
    },
  })
}

/** Conteos de la base. Solo admin; el backend responde 403 al resto. */
export function useDiagnostico(activar: boolean) {
  return useQuery({
    queryKey: ['comandas', 'diagnostico'],
    queryFn: () => comandasApi.diagnostico(),
    enabled: activar,
    staleTime: 60_000,
  })
}

/**
 * Tipos de reporte que el usuario puede generar segun su rol.
 *
 * `rol` es el rol CRUDO, no "es admin": en precarga2 los roles son `admin` y
 * `usuario`, y `lector` es un valor mas de la tabla `usuarios` que hoy nadie
 * tiene. La version anterior de esta funcion recibia `esLector = !esAdmin`,
 * lo que hacia que TODO usuario que no fuera admin contara como lector y le
 * saliera un solo boton en vez de cuatro. `erika` (rol `usuario`) no podia
 * descargar sus comandas, y el backend si se lo permitia.
 *
 * Coincide con `ROLES_REPORTE_COMPLETO` de routers/api_comandas.py. El backend
 * sigue siendo la autoridad: si el rol no alcanza, responde 403 igual. Esto
 * solo evita un boton que va a fallar.
 */
export function useReportesDisponibles(rol: string): TipoReporte[] {
  const normalizado = (rol || '').toLowerCase()
  if (normalizado === 'lector') return ['estadistico']
  return ['estadistico', 'todas', 'mortera', 'vales']
}

/** El rol es de lectura, pero puede ver el dashboard y descargar el PDF suelto. */
export function esRolLectura(rol: string): boolean {
  return (rol || '').toLowerCase() === 'lector'
}

/** Fecha a la que se mira al entrar: hoy si hay datos, si no la mas reciente. */
export function elegirFechaInicial(fechas: string[] | undefined): string | undefined {
  if (!fechas || fechas.length === 0) return undefined
  const hoy = hoyIso()
  return fechas.includes(hoy) ? hoy : fechas[0]
}

/**
 * Serie diaria de comandas por barco, para la grafica del dashboard.
 *
 * Comparte el `periodo` del selector del dashboard (14/30/180/365 dias) para que
 * las dos graficas esten mirando la misma ventana.
 *
 * A diferencia del resto de hooks de este archivo, esto NO son las comandas del
 * usuario en sesion: es un conteo global, porque la tarjeta y la grafica del
 * dashboard muestran totales de los dos barcos. La clave de cache incluye los
 * dias, asi que cambiar de periodo no ensucia la anterior.
 */
export function useSerieComandas(dias: number) {
  return useQuery({
    queryKey: ['comandas', 'serie', dias],
    queryFn: () => comandasApi.serie(dias),
    staleTime: 60_000,
  })
}
