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
import { cn } from '@/lib/utils'
import { FileText, Users, UserPlus, UserMinus, ArrowRight, Download, Building2 } from 'lucide-react'
import type { ProgramacionArea } from '@/types'

const statCards: { key: keyof DashboardStats; title: string; icon: typeof FileText; color: string }[] = [
  { key: 'total_solicitudes', title: 'Total Solicitudes', icon: FileText, color: 'text-blue-400' },
  { key: 'total_personal', title: 'Total Personal', icon: Users, color: 'text-purple-400' },
  { key: 'altas_generadas', title: 'Altas Generadas', icon: UserPlus, color: 'text-emerald-400' },
  { key: 'bajas_procesadas', title: 'Bajas Procesadas', icon: UserMinus, color: 'text-orange-400' },
  { key: 'total_companias', title: 'Compañías', icon: Building2, color: 'text-teal-400' },
]

export default function Dashboard() {
  const statsQuery = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => solicitudesApi.dashboard(),
  })

  const solicitudesQuery = useQuery({
    queryKey: ['solicitudes'],
    queryFn: () => solicitudesApi.list(1, ''),
  })

  const programacionQuery = useQuery({
    queryKey: ['programacion-dias'],
    queryFn: () => solicitudesApi.programacionDias(),
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

  const [destino, setDestino] = useState<'ambos' | 'rpx' | 'cpz'>('ambos')

  const fsBarsRpx = useFullscreen<HTMLDivElement>()
  const fsBarsCpz = useFullscreen<HTMLDivElement>()
  const fsArea = useFullscreen<HTMLDivElement>()

  const areaQuery = useQuery({
    queryKey: ['programacion-area'],
    queryFn: () => solicitudesApi.programacionArea(),
    staleTime: 60_000,
  })

  const areaData = useMemo(() => {
    const d = areaQuery.data
    if (!d) return []
    const rpx = destino === 'rpx'
    const cpz = destino === 'cpz'
    return d.dias.map((f, i) => ({
      label: new Date(`${f}T00:00:00`).toLocaleDateString('es-MX', { day: '2-digit', month: '2-digit' }),
      altas: rpx
        ? d.rpx.altas[i] ?? 0
        : cpz
          ? d.cpz.altas[i] ?? 0
          : (d.rpx.altas[i] ?? 0) + (d.cpz.altas[i] ?? 0),
      bajas: rpx
        ? d.rpx.bajas[i] ?? 0
        : cpz
          ? d.cpz.bajas[i] ?? 0
          : (d.rpx.bajas[i] ?? 0) + (d.cpz.bajas[i] ?? 0),
    }))
  }, [areaQuery.data, destino])

  const areaTooltipStyle = {
    background: '#16181d',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 8,
    fontSize: 12,
  }

  const areaChart = (
    data: { label: string; altas: number; bajas: number }[],
    loading: boolean,
    altasGrad: string,
    bajasGrad: string,
    fullscreen: boolean,
  ) => (
    <div className={cn('h-56 w-full', fullscreen && 'flex-1 min-h-0')}>
      {loading ? (
        <div className="flex h-full items-center justify-center text-muted-foreground">Cargando...</div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id={altasGrad} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#34d399" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#34d399" stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id={bajasGrad} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f87171" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#f87171" stopOpacity={0.02} />
              </linearGradient>
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
            <Area
              type="monotone"
              dataKey="altas"
              name="Altas"
              stroke="#34d399"
              strokeWidth={2}
              fill={`url(#${altasGrad})`}
            />
            <Area
              type="monotone"
              dataKey="bajas"
              name="Bajas"
              stroke="#f87171"
              strokeWidth={2}
              fill={`url(#${bajasGrad})`}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>

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
                ) : (
                  <p className="text-3xl font-bold">{value ?? 0}</p>
                )}
              </CardContent>
            </Card>
          )
        })}
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
              Programación RPX · últimos 14 días
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
              Programación CPZ · últimos 14 días
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
            Altas vs Bajas · últimos 14 días
          </CardTitle>
          <div className="flex items-center gap-2">
            <select
              value={destino}
              onChange={(e) => setDestino(e.target.value as 'ambos' | 'rpx' | 'cpz')}
              className="h-7 rounded-md border border-white/10 bg-black/30 px-2 text-xs text-sidebar-foreground outline-none focus:border-primary/50"
            >
              <option value="ambos">Ambos</option>
              <option value="rpx">RPX</option>
              <option value="cpz">CPZ</option>
            </select>
            <FullscreenToggle isFullscreen={fsArea.isFullscreen} onToggle={fsArea.toggle} />
          </div>
        </CardHeader>
        <CardContent className={cn(fsArea.isFullscreen && 'flex flex-1 flex-col min-h-0')}>
          <div className="mb-2 flex items-center gap-4 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-emerald-400" /> Altas
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-rose-400" /> Bajas
            </span>
          </div>
          {areaChart(areaData, areaQuery.isLoading, 'gradAltas', 'gradBajas', fsArea.isFullscreen)}
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
                      {s.created_at ? new Date(s.created_at).toLocaleDateString() : <span className="text-muted-foreground">—</span>}
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
