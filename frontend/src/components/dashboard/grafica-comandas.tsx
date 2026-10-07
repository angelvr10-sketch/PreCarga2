/**
 * La grafica de comandas por barco a lo largo del periodo.
 *
 * Va en el dashboard, debajo de "Altas vs Bajas", y es deliberadamente parecida
 * a esa: mismo componente Card, mismas casillas de serie interactivas, mismo
 * `useFullscreen`. La diferencia es que aqui hay DOS series (una por barco) y no
 * cuatro, asi que no hay matiz + tonalidad: cada barco tiene su color y punto.
 *
 * ── DE DONDE SALE EL BARCO ────────────────────────────────────────
 * La tabla `comandas` no tiene columna de barco. Se comprobo sobre las 5,545
 * filas: 92 destinos (POL-A, ABKATUN A, KU-A...) y CERO que mencionen RPX o CPZ.
 * El backend deduce el barco de quien subio la comanda
 * (`BARCO_POR_USUARIO` en core/comandas/serie.py). Si manana los reportes traen
 * el barco, se cambia ahi, no aqui.
 *
 * ── COLORES ───────────────────────────────────────────────────────
 * Amarillo y rojo, como se pidio. Los dos tonos pasan el minimo de contraste de
 * 3:1 (WCAG 1.4.11) contra el fondo de la tarjeta (#222225):
 *
 *   RPX  amber-400  #fbbf24 -> 9.50:1
 *   CPZ  red-400    #f87171 -> 5.74:1
 *
 * Pero amarillo y rojo son tonos calidos muy juntos, y con daltonismo
 * protan/deutan se pueden confundir. Por eso CPZ va punteado y RPX continuo:
 * el patron es una codificacion REDUNDANTE del barco, igual que "Altas vs Bajas"
 * hace con las bajas. El color no tiene que ser el unico canal.
 */
import { useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AlertCircle, Check } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { FullscreenToggle } from '@/components/ui/fullscreen-toggle'
import { useFullscreen } from '@/hooks/use-fullscreen'
import { useSerieComandas } from '@/hooks/use-comandas'
import { cn } from '@/lib/utils'

/** Las dos series. El orden fija el de la leyenda y el de las casillas. */
const SERIES = [
  { key: 'rpx', label: 'RPX', color: '#fbbf24', dashed: false },  // amber-400
  { key: 'cpz', label: 'CPZ', color: '#f87171', dashed: true },   // red-400
] as const

type ClaveSerie = (typeof SERIES)[number]['key']
type FilaSerie = { label: string } & Record<ClaveSerie, number>

interface Props {
  /** El mismo periodo que el selector del dashboard. */
  dias: number
  /** 'últimos 30 días'. Sale de PERIODOS, para el titulo. */
  periodoLabel: string
}

export function GraficaComandasPorBarco({ dias, periodoLabel }: Props) {
  const query = useSerieComandas(dias)
  const fs = useFullscreen<HTMLDivElement>()

  // Las dos arrancan visibles: el grafico completo es el estado por defecto y
  // las casillas sirven para aislar, no para construir.
  const [seriesOn, setSeriesOn] = useState<Record<ClaveSerie, boolean>>({
    rpx: true,
    cpz: true,
  })

  const activas = SERIES.filter((s) => seriesOn[s.key]).length

  // La ultima serie activa no se puede apagar: un grafico sin ninguna serie
  // visible parece roto, no "sin datos".
  const toggleSerie = (key: ClaveSerie) =>
    setSeriesOn((prev) => (prev[key] && activas === 1 ? prev : { ...prev, [key]: !prev[key] }))

  const datos = query.data

  // Las etiquetas salen de las FECHAS que devuelve el backend, no de una serie
  // de valores: si vinieran de `rpx`, un dia con 0 comandas no tendria etiqueta
  // y el eje X se descuadraria contra CPZ.
  const filas = useMemo<FilaSerie[]>(() => {
    if (!datos) return []
    return datos.dias.map((f, i) => ({
      label: new Date(`${f}T00:00:00`).toLocaleDateString('es-MX', {
        day: '2-digit',
        month: '2-digit',
      }),
      rpx: datos.rpx[i] ?? 0,
      cpz: datos.cpz[i] ?? 0,
    }))
  }, [datos])

  const totalRpx = useMemo(() => (datos ? datos.rpx.reduce((a, b) => a + b, 0) : 0), [datos])
  const totalCpz = useMemo(() => (datos ? datos.cpz.reduce((a, b) => a + b, 0) : 0), [datos])

  // Sin esto, un usuario nuevo en el mapa haria que la suma de las series no
  // cuadre con el total, y el grafico pareceria mentir sin avisar.
  const sinAsignar = datos?.sin_asignar ?? 0

  const tooltipStyle = {
    background: '#16181d',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 8,
    fontSize: 12,
  }

  return (
    <Card
      ref={fs.ref}
      className={cn(
        fs.isFullscreen && 'flex flex-col',
        fs.isFullscreen && !fs.native && 'fixed inset-0 z-50 overflow-auto bg-background p-2',
      )}
    >
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Comandas por barco · {periodoLabel}
        </CardTitle>
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-amber-400">{totalRpx.toLocaleString()}</span>
          <FullscreenToggle isFullscreen={fs.isFullscreen} onToggle={fs.toggle} />
        </div>
      </CardHeader>
      <CardContent className={cn(fs.isFullscreen && 'flex flex-1 flex-col min-h-0')}>
        {/* Las casillas sustituyen a la leyenda estatica, como en Altas vs Bajas. */}
        <div className="mb-3 flex flex-wrap items-center gap-1.5">
          {SERIES.map((s) => {
            const on = seriesOn[s.key]
            const ultimaActiva = on && activas === 1
            const total = s.key === 'rpx' ? totalRpx : totalCpz
            return (
              <button
                key={s.key}
                type="button"
                role="checkbox"
                aria-checked={on}
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
                <span className="tabular-nums opacity-70">{total.toLocaleString()}</span>
              </button>
            )
          })}
        </div>

        <div className={cn('h-56 w-full', fs.isFullscreen && 'flex-1 min-h-0')}>
          {query.isLoading ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              Cargando...
            </div>
          ) : query.isError ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
              <AlertCircle className="h-6 w-6 text-destructive" />
              <span className="text-xs">Error al cargar las comandas</span>
            </div>
          ) : filas.length === 0 ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              <span className="text-sm">Sin comandas en este periodo</span>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={filas}>
                <defs>
                  {SERIES.map((s) => (
                    <linearGradient key={s.key} id={`grad-com-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={s.color} stopOpacity={0.28} />
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
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(v, name) => [`${v} comandas`, String(name)]}
                />
                {/* `hide` tambien quita la serie del calculo del eje Y, asi que
                    apagar una serie reescala el eje a lo que queda en vez de dejar
                    el grafico aplastado contra el cero. */}
                {SERIES.map((s) => (
                  <Area
                    key={s.key}
                    type="monotone"
                    dataKey={s.key}
                    name={s.label}
                    stroke={s.color}
                    strokeWidth={2}
                    strokeDasharray={s.dashed ? '6 4' : undefined}
                    fill={`url(#grad-com-${s.key})`}
                    hide={!seriesOn[s.key]}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {sinAsignar > 0 && (
          <p className="mt-2 text-xs text-amber-500/90">
            {sinAsignar.toLocaleString()} comandas del periodo todavia no tienen barco
            asignado: no aparecen en ninguna de las dos series.
          </p>
        )}
      </CardContent>
    </Card>
  )
}