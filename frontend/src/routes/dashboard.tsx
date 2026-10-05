import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { useMemo, useState } from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  AreaChart,
  Area,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { FullscreenToggle } from '@/components/ui/fullscreen-toggle'
import { useFullscreen } from '@/hooks/use-fullscreen'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { solicitudesApi } from '@/lib/solicitudes'
import type { DashboardStats } from '@/types'
import { cn, formatFecha } from '@/lib/utils'
import { FileText, ArrowRightLeft, UserPlus, UserMinus, ArrowRight, Download, Building2, AlertCircle, Check } from 'lucide-react'
import type { ProgramacionArea } from '@/types'

type Periodo = 14 | 30 | 180 | 365

const PERIODOS: { value: Periodo; label: string; plural: string }[] = [
  { value: 14, label: '14 días', plural: 'últimos 14 días' },
  { value: 30, label: '1 mes', plural: 'últimos 30 días' },
  { value: 180, label: '6 meses', plural: 'últimos 6 meses' },
  { value: 365, label: '1 año', plural: 'últimos 365 días' },
]

// `hint` documenta la unidad de cada tarjeta. Sin esto "Altas Generadas 5059"
// es ambiguo: son personas, no folios, y esa confusion es la que hace dudar
// de los numeros sin poder contrastarlos con la BD.
const statCards: {
  key: keyof DashboardStats
  title: string
  hint: string
  icon: typeof FileText
  color: string
}[] = [
  { key: 'total_solicitudes', title: 'Total Solicitudes', hint: 'folios registrados', icon: FileText, color: 'text-blue-400' },
  { key: 'total_movimientos', title: 'Total Movimientos', hint: 'altas + bajas', icon: ArrowRightLeft, color: 'text-purple-400' },
  { key: 'altas_generadas', title: 'Altas Generadas', hint: 'personas que suben', icon: UserPlus, color: 'text-emerald-400' },
  { key: 'bajas_procesadas', title: 'Bajas Procesadas', hint: 'personas que bajan', icon: UserMinus, color: 'text-orange-400' },
  { key: 'total_companias', title: 'Compañías', hint: 'razones sociales', icon: Building2, color: 'text-teal-400' },
]

// Las 4 series de "Altas vs Bajas", todas en la misma grafica.
// Codificacion en dos ejes:
//   - MATIZ  = destino (violeta = RPX, cielo = CPZ, igual que las barras de
//     arriba y los badges de destino).
//   - TONALIDAD = tipo: altas en el tono claro del matiz (los mismos hex que
//     las barras, para que el color signifique lo mismo en toda la pagina) y
//     bajas en el tono profundo del mismo matiz. Asi RPX Altas vs RPX Bajas se
//     distinguen por profundidad sin inventar un cuarto color.
// El punteado en bajas se mantiene como codificacion redundante de "bajas":
// el color solo no basta para lectura daltonica.
const AREA_SERIES = [
  // Los tonos de bajas se oscurecen para abrir el escalon de tonalidad, pero
  // sin bajar del minimo de contraste 3:1 (WCAG 1.4.11) contra el fondo de la
  // tarjeta (#222225). Medido sobre ese fondo:
  //   violet-600 #7c3aed -> 2.78:1  FALLA, asi que bajas se queda en violet-500.
  //   sky-600    #0284c7 -> 3.87:1  pasa, y el tono claro del cielo ya es muy
  //                              brillante, por eso si admite un paso mas
  //                              profundo que el violeta.
  { key: 'rpxAltas', label: 'RPX Altas', color: '#a78bfa', fill: 0.28, dashed: false }, // violet-400 · 5.83:1
  { key: 'rpxBajas', label: 'RPX Bajas', color: '#8b5cf6', fill: 0.32, dashed: true }, // violet-500 · 3.75:1
  { key: 'cpzAltas', label: 'CPZ Altas', color: '#38bdf8', fill: 0.28, dashed: false }, // sky-400 · 7.41:1
  { key: 'cpzBajas', label: 'CPZ Bajas', color: '#0284c7', fill: 0.4, dashed: true }, // sky-600 · 3.87:1
] as const

type AreaKey = (typeof AREA_SERIES)[number]['key']
type AreaRow = { label: string } & Record<AreaKey, number>

export default function Dashboard() {
  const [periodo, setPeriodo] = useState<Periodo>(30)

  const periodoLabel = PERIODOS.find((p) => p.value === periodo)?.plural ?? 'últimos 30 días'

  const statsQuery = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => solicitudesApi.dashboard(),
  })

  const solicitudesQuery = useQuery({
    queryKey: ['solicitudes'],
    queryFn: () => solicitudesApi.list(1, ''),
  })

  const programacionQuery = useQuery({
    queryKey: ['programacion-dias', periodo],
    queryFn: () => solicitudesApi.programacionDias(periodo),
    staleTime: 60_000,
  })

  const areaQuery = useQuery({
    queryKey: ['programacion-area', periodo],
    queryFn: () => solicitudesApi.programacionArea(periodo),
    staleTime: 60_000,
  })

  const stats = statsQuery.data
  const solicitudes = solicitudesQuery.data?.solicitudes ?? []
  const programacion = programacionQuery.data

  const barData = useMemo(() => {
    if (!programacion) return []
    return programacion.dias.map((d, i) => ({
      label: new Date(`${d}T00:00:00`).toLocaleDateString('es-MX', { day: '2-digit', month: '2-digit' }),
      rpx: programacion.rpx[i] ?? 0,
      cpz: programacion.cpz[i] ?? 0,
    }))
  }, [programacion])

  const totalRpx = useMemo(() => barData.reduce((acc, d) => acc + d.rpx, 0), [barData])
  const totalCpz = useMemo(() => barData.reduce((acc, d) => acc + d.cpz, 0), [barData])

  // Las 4 arrancan visibles: el chart completo es el estado por defecto y las
  // casillas sirven para aislar una serie, no para construirla a piezas.
  const [seriesOn, setSeriesOn] = useState<Record<AreaKey, boolean>>({
    rpxAltas: true,
    rpxBajas: true,
    cpzAltas: true,
    cpzBajas: true,
  })

  const seriesActivas = AREA_SERIES.filter((s) => seriesOn[s.key]).length

  // La ultima serie activa no se puede apagar: un chart sin ninguna serie
  // visible parece roto, no "sin datos".
  const toggleSerie = (key: AreaKey) =>
    setSeriesOn((prev) =>
      prev[key] && seriesActivas === 1 ? prev : { ...prev, [key]: !prev[key] },
    )

  const fsBarsRpx = useFullscreen<HTMLDivElement>()
  const fsBarsCpz = useFullscreen<HTMLDivElement>()
  const fsArea = useFullscreen<HTMLDivElement>()

  // Las 4 series salen del mismo payload de /programacion-area: el backend ya
  // devolvia rpx.altas/bajas y cpz.altas/bajas, pero antes se sumaban en un
  // solo par segun el destino. Ahora se exponen por separado, sin transformar.
  const areaData = useMemo<AreaRow[]>(() => {
    const d = areaQuery.data
    if (!d) return []
    return d.dias.map((f, i) => ({
      label: new Date(`${f}T00:00:00`).toLocaleDateString('es-MX', { day: '2-digit', month: '2-digit' }),
      rpxAltas: d.rpx.altas[i] ?? 0,
      rpxBajas: d.rpx.bajas[i] ?? 0,
      cpzAltas: d.cpz.altas[i] ?? 0,
      cpzBajas: d.cpz.bajas[i] ?? 0,
    }))
  }, [areaQuery.data])

  const areaTooltipStyle = {
    background: '#16181d',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 8,
    fontSize: 12,
  }

  const areaChart = (data: AreaRow[], loading: boolean, error: boolean, fullscreen: boolean) => (
    <div className={cn('h-56 w-full', fullscreen && 'flex-1 min-h-0')}>
      {loading ? (
        <div className="flex h-full items-center justify-center text-muted-foreground">Cargando...</div>
      ) : error ? (
        <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
          <AlertCircle className="h-6 w-6 text-destructive" />
          <span className="text-xs">Error al cargar datos</span>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              {AREA_SERIES.map((s) => (
                <linearGradient key={s.key} id={`grad-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={s.color} stopOpacity={s.fill} />
                  <stop offset="100%" stopColor={s.color} stopOpacity={0.02} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis
              dataKey="label"
              stroke="rgba(255,255,255,0.5)"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              stroke="rgba(255,255,255,0.5)"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              width={32}
            />
            <Tooltip contentStyle={areaTooltipStyle} />
            {/* `hide` no solo oculta la serie: recharts filtra los items
                ocultos al calcular el dominio del eje Y (selectUnfilteredCartesianItems
                -> `return !item.hide`), asi que el eje se reescala a lo que queda
                visible en vez de dejar la grafica aplastada. */}
            {AREA_SERIES.map((s) => (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.label}
                stroke={s.color}
                strokeWidth={2}
                strokeDasharray={s.dashed ? '6 4' : undefined}
                fill={`url(#grad-${s.key})`}
                hide={!seriesOn[s.key]}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {statCards.map((card) => {
          const Icon = card.icon
          const value = stats?.[card.key]
          return (
            <Card key={card.key}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {card.title}
                </CardTitle>
                <Icon className={`h-5 w-5 ${card.color}`} />
              </CardHeader>
              <CardContent>
                {statsQuery.isLoading ? (
                  <div className="h-8 w-20 animate-pulse rounded bg-muted" />
                ) : statsQuery.isError ? (
                  <div className="flex items-center gap-1 text-destructive">
                    <AlertCircle className="h-4 w-4" />
                    <span className="text-xs">Error</span>
                  </div>
                ) : (
                  <>
                    {/* tabular-nums + toLocaleString: los cinco numeros deben
                        escanear en paralelo y con el mismo formato que los
                        totales de las graficas de abajo. */}
                    <p className="text-3xl font-bold tabular-nums">
                      {typeof value === 'number' ? value.toLocaleString('es-MX') : '—'}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">{card.hint}</p>
                  </>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="flex flex-wrap items-center gap-1 rounded-lg border border-white/10 bg-black/30 p-1 w-fit">
        {PERIODOS.map((p) => (
          <button
            key={p.value}
            onClick={() => setPeriodo(p.value)}
            className={cn(
              'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
              periodo === p.value
                ? 'bg-primary text-primary-foreground shadow'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card
          ref={fsBarsRpx.ref}
          className={cn(
            fsBarsRpx.isFullscreen && 'flex flex-col',
            fsBarsRpx.isFullscreen && !fsBarsRpx.native && 'fixed inset-0 z-50 overflow-auto bg-background p-2',
          )}
        >
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Programación RPX · {periodoLabel}
            </CardTitle>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-violet-400">{totalRpx.toLocaleString()}</span>
              <FullscreenToggle isFullscreen={fsBarsRpx.isFullscreen} onToggle={fsBarsRpx.toggle} />
            </div>
          </CardHeader>
          <CardContent className={cn(fsBarsRpx.isFullscreen && 'flex flex-1 flex-col min-h-0')}>
            <div className={cn('h-56 w-full', fsBarsRpx.isFullscreen && 'flex-1 min-h-0')}>
              {programacionQuery.isLoading ? (
                <div className="flex h-full items-center justify-center text-muted-foreground">Cargando...</div>
              ) : programacionQuery.isError ? (
                <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
                  <AlertCircle className="h-6 w-6 text-destructive" />
                  <span className="text-xs">Error al cargar datos</span>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={barData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                    <XAxis
                      dataKey="label"
                      stroke="rgba(255,255,255,0.5)"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      stroke="rgba(255,255,255,0.5)"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                      width={32}
                    />
                    <Tooltip
                      cursor={{ fill: 'rgba(255,255,255,0.06)' }}
                      contentStyle={{ background: '#16181d', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
                      formatter={(value) => [`${value} personas`, 'RPX']}
                    />
                    <Bar dataKey="rpx" fill="#a78bfa" radius={[4, 4, 0, 0]} maxBarSize={42} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>

        <Card
          ref={fsBarsCpz.ref}
          className={cn(
            fsBarsCpz.isFullscreen && 'flex flex-col',
            fsBarsCpz.isFullscreen && !fsBarsCpz.native && 'fixed inset-0 z-50 overflow-auto bg-background p-2',
          )}
        >
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Programación CPZ · {periodoLabel}
            </CardTitle>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-sky-300">{totalCpz.toLocaleString()}</span>
              <FullscreenToggle isFullscreen={fsBarsCpz.isFullscreen} onToggle={fsBarsCpz.toggle} />
            </div>
          </CardHeader>
          <CardContent className={cn(fsBarsCpz.isFullscreen && 'flex flex-1 flex-col min-h-0')}>
            <div className={cn('h-56 w-full', fsBarsCpz.isFullscreen && 'flex-1 min-h-0')}>
              {programacionQuery.isLoading ? (
                <div className="flex h-full items-center justify-center text-muted-foreground">Cargando...</div>
              ) : programacionQuery.isError ? (
                <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
                  <AlertCircle className="h-6 w-6 text-destructive" />
                  <span className="text-xs">Error al cargar datos</span>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={barData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                    <XAxis
                      dataKey="label"
                      stroke="rgba(255,255,255,0.5)"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      stroke="rgba(255,255,255,0.5)"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                      width={32}
                    />
                    <Tooltip
                      cursor={{ fill: 'rgba(255,255,255,0.06)' }}
                      contentStyle={{ background: '#16181d', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
                      formatter={(value) => [`${value} personas`, 'CPZ']}
                    />
                    <Bar dataKey="cpz" fill="#38bdf8" radius={[4, 4, 0, 0]} maxBarSize={42} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card
        ref={fsArea.ref}
        className={cn(
          fsArea.isFullscreen && 'flex flex-col',
          fsArea.isFullscreen && !fsArea.native && 'fixed inset-0 z-50 overflow-auto bg-background p-2',
        )}
      >
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Altas vs Bajas · {periodoLabel}
          </CardTitle>
          <FullscreenToggle isFullscreen={fsArea.isFullscreen} onToggle={fsArea.toggle} />
        </CardHeader>
        <CardContent className={cn(fsArea.isFullscreen && 'flex flex-1 flex-col min-h-0')}>
          {/* Las casillas sustituyen a la leyenda estatica: el legend ahora es
              interactivo, asi que no hace falta duplicar la info en dos sitios. */}
          <div className="mb-3 flex flex-wrap items-center gap-1.5">
            {AREA_SERIES.map((s) => {
              const on = seriesOn[s.key]
              const ultimaActiva = on && seriesActivas === 1
              return (
                <button
                  key={s.key}
                  type="button"
                  role="checkbox"
                  aria-checked={on}
                  // La ultima serie no se puede apagar: un chart vacio no
                  // comunica "sin datos", parece roto.
                  disabled={ultimaActiva}
                  onClick={() => toggleSerie(s.key)}
                  className={cn(
                    'inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-medium transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60',
                    ultimaActiva && 'cursor-not-allowed opacity-60',
                    !on && 'border-white/10 text-muted-foreground hover:text-foreground',
                  )}
                  style={
                    on
                      ? { backgroundColor: `${s.color}1f`, borderColor: `${s.color}80`, color: s.color }
                      : undefined
                  }
                >
                  <span
                    className={cn(
                      'flex h-3 w-3 shrink-0 items-center justify-center rounded-[3px] border',
                      on ? 'border-transparent' : 'border-white/25',
                    )}
                  >
                    {on && <Check className="h-2.5 w-2.5" strokeWidth={3.5} />}
                  </span>
                  {s.label}
                </button>
              )
            })}
          </div>
          {areaChart(areaData, areaQuery.isLoading, areaQuery.isError, fsArea.isFullscreen)}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Solicitudes Recientes</CardTitle>
          <Button variant="outline" size="sm" asChild>
            <Link to="/altas">
              Ver todas
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>N° Solicitud</TableHead>
                <TableHead>Fecha de Llegada</TableHead>
                <TableHead>Destino</TableHead>
                <TableHead>Compañía</TableHead>
                <TableHead className="text-right">Suben</TableHead>
                <TableHead className="text-right">Bajan</TableHead>
                <TableHead>Descargar</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {solicitudesQuery.isLoading ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                    <div className="flex items-center justify-center gap-2">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                      Cargando...
                    </div>
                  </TableCell>
                </TableRow>
              ) : solicitudesQuery.isError ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                    <div className="flex flex-col items-center gap-2">
                      <AlertCircle className="h-6 w-6 text-destructive" />
                      <span className="text-xs">Error al cargar solicitudes</span>
                    </div>
                  </TableCell>
                </TableRow>
              ) : solicitudes.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                    No hay solicitudes recientes
                  </TableCell>
                </TableRow>
              ) : (
                solicitudes.slice(0, 5).map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-medium">{s.folio}</TableCell>
                    <TableCell>
                      {s.created_at ? formatFecha(s.created_at) : <span className="text-muted-foreground">—</span>}
                    </TableCell>
                    <TableCell>
                      {s.destino ? (
                        <span className={cn(
                          'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold',
                          s.destino.toUpperCase() === 'CPZ'
                            ? 'bg-sky-500/15 text-sky-300'
                            : s.destino.toUpperCase() === 'RPX'
                              ? 'bg-violet-500/15 text-violet-300'
                              : 'bg-muted text-muted-foreground',
                        )}>
                          {s.destino}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>{s.compania || <span className="text-muted-foreground">—</span>}</TableCell>
                    <TableCell className="text-right font-semibold text-emerald-400">{s.personal_count ?? 0}</TableCell>
                    <TableCell className="text-right font-semibold text-destructive">{s.bajas_count ?? 0}</TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm" className="gap-2" asChild>
                        <a href={`/api/descargar/${s.folio}.xlsx`} target="_blank" rel="noreferrer">
                          <Download className="h-4 w-4" />
                        </a>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
