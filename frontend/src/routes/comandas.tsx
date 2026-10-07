/**
 * /comandas — la pantalla completa, en una sola pagina.
 *
 * Sustituye a la app de Streamlit. La estructura es la misma de arriba abajo:
 * selector de fecha, subida del reporte, KPIs, gráficas, tabla de comandas y
 * descargas.
 *
 * Tres cosas que aqui se resuelven de otra forma que en la app vieja:
 *
 * 1. LA FECHA ES UN SELECTOR DE UNA LISTA, no un calendario. Las fechas con
 *    datos son pocas y exactas: vienen de `/api/comandas/fechas`. Un calendario
 *    obligaria a adivinar y luego a un fetch por cada dia que se cliquea, para
 *    acabar con "no hay datos para ese dia" la mitad de las veces.
 *
 * 2. LOS PDF SE GENERAN AL PEDIRLOS. La app vieja generaba los cuatro en cada
 *    rerun aunque nadie los abriera (app.py:1698-1728).
 *
 * 3. EL USUARIO VIENE DE LA SESION. `useAuth` ya sabe quien es y si es admin;
 *    no hay login aqui.
 */
import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Card, CardContent, CardHeader, CardTitle,
} from '@/components/ui/card'
import { notificar } from '@/hooks/use-toast'
import { useAuth } from '@/hooks/use-auth'
import {
  elegirFechaInicial,
  esRolLectura,
  useComandas,
  useDiagnostico,
  useEstadisticas,
  useFechas,
  useImportar,
  useReportesDisponibles,
} from '@/hooks/use-comandas'
import { BotonesReporte } from '@/components/comandas/botones-reporte'
import { Dropzone } from '@/components/comandas/dropzone'
import { Graficas } from '@/components/comandas/graficas'
import { KpiGrid } from '@/components/comandas/kpi-grid'
import { TablaComandas } from '@/components/comandas/tabla-comandas'
import { TablaPax } from '@/components/comandas/tabla-pax'
import { fechaCorta, fechaLarga, descargarComanda, descargarReporte } from '@/lib/comandas'
import { mensajeDescargaError } from '@/lib/solicitudes'
import { ApiError } from '@/lib/api'
import type { TipoReporte } from '@/types/comandas'
import { CalendarDays, Loader2, RefreshCw, ScrollText, ChevronDown } from 'lucide-react'

export default function Comandas() {
  const { user } = useAuth()

  // El rol crudo, no `!admin`. Con solo el booleano, una usuaria con rol
  // 'usuario' (que NO es lector) se contabilizaba como lector y le salia un
  // solo boton de descarga. El backend si le permitia los cuatro.
  const tiposDisponibles = useReportesDisponibles(user?.rol ?? '')
  const esLector = esRolLectura(user?.rol ?? '')
  // El diagnostico cuenta datos de TODOS los usuarios: solo admin de verdad.
  const esAdmin = !!user?.admin

  const {
    data: fechas,
    isLoading: cargandoFechas,
    refetch: recargarFechas,
  } = useFechas()
  const [fecha, setFecha] = useState<string | undefined>(undefined)
  const [descargando, setDescargando] = useState<string | null>(null)
  const [verDiagnostico, setVerDiagnostico] = useState(false)

  const { data: respuesta, isLoading: cargandoComandas } = useComandas(fecha)
  const { data: stats } = useEstadisticas(fecha)
  const importar = useImportar()
  const diagnostico = useDiagnostico(esAdmin && verDiagnostico)

  // Al entrar: hoy si hay comandas de hoy, si no la fecha mas reciente.
  const inicial = useMemo(() => elegirFechaInicial(fechas), [fechas])
  useEffect(() => {
    if (fecha === undefined && inicial) setFecha(inicial)
  }, [inicial, fecha])

  const comandas = respuesta?.comandas ?? []
  const hayDatos = comandas.length > 0

  /* ── Subir reporte ─────────────────────────────────────────── */

  async function subir(archivo: File) {
    try {
      const r = await importar.mutateAsync(archivo)

      notificar(
        `${r.total} comandas guardadas`,
        `Fecha ${fechaCorta(r.fecha)} · ${r.total_pax} PAX · ${r.morteras} morteras`,
        'exito',
      )

      // La fecha puede ser nueva: se selecciona para que se vea lo recien subido.
      setFecha(r.fecha)

      // Las advertencias del backend son avisos, no fallos. Se muestran aparte
      // porque el usuario debe saber que faltaron folios, aunque se haya
      // guardado todo lo demas.
      if (r.advertencias.length > 0) {
        notificar(
          'Guardado con observaciones',
          r.advertencias.join(' · '),
          'aviso',
          )
      }
    } catch (e) {
      const mensaje =
        e instanceof ApiError
          ? e.message
          : 'No se pudo procesar el archivo. Intenta de nuevo.'
      notificar('No se pudo subir el reporte', mensaje, 'error')
    }
  }

  /* ── Descargas ────────────────────────────────────────────── */

  async function bajar(tipo: TipoReporte): Promise<boolean> {
    if (!fecha) return false
    setDescargando(tipo)
    try {
      const r = await descargarReporte(tipo, fecha)
      if (!r.ok) {
        notificar('No se pudo descargar', mensajeDescargaError(r.motivo), 'error')
      }
      return r.ok
    } finally {
      setDescargando(null)
    }
  }

  async function bajarComanda(folio: string): Promise<boolean> {
    if (!fecha) return false
    setDescargando(folio)
    try {
      const r = await descargarComanda(folio, fecha)
      if (!r.ok) {
        notificar('No se pudo descargar', mensajeDescargaError(r.motivo), 'error')
      }
      return r.ok
    } finally {
      setDescargando(null)
    }
  }

  /* ── Render ───────────────────────────────────────────────── */

  if (cargandoFechas) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Cargando comandas…
      </div>
    )
  }

  const sinFechas = !fechas || fechas.length === 0

  /*
    Los 4 botones de descarga se declaran aqui y se reutilizan en varias ramas
    del JSX. Antes se pintaban al final de la pagina, debajo de todo; ahora van
    entre las graficas y la tabla, que es donde se buscan.

    Se declaran una vez para que el panel no dependa de que haya datos: se pinte
    donde se pinte, si no hay comandas aparece deshabilitado con el motivo
    escrito encima. Ocultarlo era PEOR que la app de Streamlit, que al menos
    mostraba un `st.info` ("No hay datos disponibles para generar reportes PDF en
    esta fecha"). Sin ningun indicio, la conclusion de quien lo ve es "faltan los
    botones".
  */
  const botones = (
    <BotonesReporte
      tipos={tiposDisponibles}
      onDescargar={bajar}
      disabled={!hayDatos || !fecha}
      motivoDeshabilitado={
        !fecha || sinFechas
          ? 'Todavía no hay comandas guardadas. Sube un reporte para poder generar los PDF.'
          : !hayDatos
            ? `No hay comandas del ${fecha ? fechaCorta(fecha) : ''} para generar PDF. Cambia de fecha o sube el reporte de ese día.`
            : esLector
              ? 'Tu rol solo puede generar el reporte estadístico y el PDF de una comanda suelta.'
              : undefined
      }
    />
  )

  return (
    <div className="space-y-5">
      {/* ── Encabezado ──────────────────────────────────────── */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">
            Comandas de Alimentos
          </h1>
          <p className="text-sm text-muted-foreground">
            Sistema de gestión · Alimentos al área
          </p>
        </div>

        <div className="flex items-center gap-2">
          {fecha && (
            <span className="hidden text-xs capitalize text-muted-foreground sm:inline">
              {fechaLarga(fecha)}
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            disabled={sinFechas}
            title="Recargar desde la base"
            onClick={() => void recargarFechas()}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Actualizar
          </Button>
        </div>
      </div>

      {/* ── Fecha + subida ──────────────────────────────────── */}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,340px)_1fr]">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              <CalendarDays className="h-3.5 w-3.5" />
              Fecha de operación
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {sinFechas ? (
              <p className="py-2 text-sm text-muted-foreground">
                Todavía no hay comandas guardadas. Sube un reporte para empezar.
              </p>
            ) : (
              <>
                <div className="relative">
                  <select
                    value={fecha ?? ''}
                    onChange={(e) => setFecha(e.target.value)}
                    className="h-10 w-full appearance-none rounded-md border border-input bg-background px-3 pr-9 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  >
                    {fechas.map((f) => (
                      <option key={f} value={f}>{fechaCorta(f)}</option>
                    ))}
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                </div>
                <p className="text-xs capitalize text-muted-foreground">
                  {fecha ? fechaLarga(fecha) : ''}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              📂 Reporte de comandas
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Dropzone onSubir={subir} subiendo={importar.isPending} />
          </CardContent>
        </Card>
      </div>

      {/* ── Diagnostico (admin) ─────────────────────────────── */}
      {esAdmin && (
        <div className="flex items-start gap-2 text-xs">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1.5 text-muted-foreground"
            onClick={() => setVerDiagnostico((v) => !v)}
          >
            <ScrollText className="h-3.5 w-3.5" />
            Diagnóstico
          </Button>
          {verDiagnostico && diagnostico.data && (
            <pre className="flex-1 overflow-auto rounded-md border border-border/60 bg-muted/40 p-2.5 text-[11px] leading-relaxed">
              {`usuario: ${diagnostico.data.usuario}
comandas en la tabla: ${diagnostico.data.comandas_en_tabla}
tuyas: ${diagnostico.data.mis_comandas}
tus fechas: ${diagnostico.data.mis_fechas}
${diagnostico.data.error ? `error: ${diagnostico.data.error}` : ''}`}
            </pre>
          )}
        </div>
      )}

      {/* ── Contenido ─────────────────────────────────────────── */}
      {sinFechas ? (
        <>
          <Card>
            <CardContent className="flex flex-col items-center gap-2 py-16 text-center">
              <p className="text-sm font-medium">Sin comandas todavía</p>
              <p className="max-w-md text-sm text-muted-foreground">
                Sube el reporte PDF del día arriba. Las comandas se guardan por fecha
                y las puedes volver a descargar como PDF.
              </p>
            </CardContent>
          </Card>
          {botones}
        </>
      ) : !hayDatos ? (
        <>
          <Card>
            <CardContent className="py-10 text-center text-sm text-muted-foreground">
              No hay comandas para el {fecha ? fechaCorta(fecha) : ''}. Sube el
              reporte de ese día.
            </CardContent>
          </Card>
          {botones}
        </>
      ) : (
        <>
          {/* ── KPIs ───────────────────────────────────────── */}
          {stats && <KpiGrid stats={stats} />}

          {/* ── Graficas + tablas ──────────────────────────── */}
          {stats && (
            <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-[1fr_1fr_1.1fr]">
              <TablaPax
                titulo="PAX por Destino"
                icono="📍"
                conteo={stats.por_destino}
                total={stats.total_alimentos}
              />
              <TablaPax
                titulo="PAX por Compañía"
                icono="🏢"
                conteo={stats.por_compania}
                total={stats.total_alimentos}
              />
              <Graficas
                porDestino={stats.por_destino_grafico}
                porTransporte={stats.por_transporte}
                totalPax={stats.total_alimentos}
              />
            </div>
          )}

          {/* ── Generar PDF ────────────────────────────────── */}
          {botones}

          {/* ── Tabla ──────────────────────────────────────── */}
          <Card>
            <CardContent className="pt-6">
              <TablaComandas
                comandas={comandas}
                fecha={fecha ?? ''}
                onDescargar={bajarComanda}
                descargando={descargando}
              />
            </CardContent>
          </Card>
        </>
      )}

      {cargandoComandas && (
        <p className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          Cargando comandas…
        </p>
      )}
    </div>
  )
}
