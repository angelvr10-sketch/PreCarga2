/**
 * Las graficas del dashboard: donut de PAX por destino y barras por transporte.
 *
 * Recharts, que ya venia en precarga2 (migrado de plotly en la app de Streamlit).
 * Los valores salen de `por_destino_grafico` y `por_transporte`, que el backend
 * ya calculo y con los nombres de destino abreviados (`KU-A (G)`) para que quepan
 * en la leyenda.
 */
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { aFilas } from '@/lib/comandas'

/** Misma paleta que usaba la app de Streamlit (app.py:1629-1631). */
const PALETA = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#14b8a6',
  '#f97316', '#ec4899', '#6366f1', '#84cc16', '#0ea5e9', '#a855f7']

/**
 * Los aereos van en gris.
 *
 * No van a ningun destino concreto, asi que no compiten por el color de una
 * plataforma: si tomaran un color de la paleta, parecerian un destino mas.
 */
const COLOR_AEREOS = '#64748b'

/**
 * Recharts 3 tipa los formadores con `ValueType | undefined`, asi que el
 * parametro llega como `unknown`. Estos ayudantes lo estrechan a numero con un
 * valor por defecto: los conteos siempre son enteros, y un undefined solo
 * aparece si el grafico se pinta sin datos.
 */
function aNumero(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

const TOOLTIP_ESTILO = {
  contentStyle: {
    backgroundColor: 'hsl(var(--popover))',
    border: '1px solid hsl(var(--border))',
    borderRadius: '0.5rem',
    fontSize: '0.8rem',
  },
  labelStyle: { color: 'hsl(var(--foreground))' },
}

interface Props {
  porDestino: Record<string, number>
  porTransporte: Record<string, number>
  totalPax: number
}

export function Graficas({ porDestino, porTransporte, totalPax }: Props) {
  const destino = aFilas(porDestino)
  const transporte = aFilas(porTransporte)

  // El color sale de la POSICION en el ranking, no del texto: un mismo destino
// conserva su color mientras no le cambien el lugar, igual que en la app.
const coloresDestino = destino.map((d, i) =>
    d.nombre === 'AÉREOS' ? COLOR_AEREOS : PALETA[i % PALETA.length],
  )

  // Colores estables por transporte: el mismo transporte conserva su color
  // entre recargas, en vez de cambiar segun el orden alfabetico.
  const colorDeTransporte = (nombre: string) => {
    const orden = [...new Set(transporte.map((t) => t.nombre))].sort()
    return PALETA[orden.indexOf(nombre) % PALETA.length]
  }

  return (
    <>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            🥧 Distribución por Destino
          </CardTitle>
        </CardHeader>
        <CardContent>
          {destino.length === 0 ? (
            <p className="py-16 text-center text-sm text-muted-foreground">
              Sin datos para graficar
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={destino}
                  dataKey="pax"
                  nameKey="nombre"
                  cx="50%"
                  cy="50%"
                  innerRadius="45%"
                  outerRadius="78%"
                  paddingAngle={1}
                  stroke="hsl(var(--border))"
                  strokeWidth={1}
                >
                  {destino.map((d, i) => (
                    <Cell key={d.nombre} fill={coloresDestino[i]} />
                  ))}
                </Pie>
                <Tooltip {...TOOLTIP_ESTILO} formatter={(v) => [`${aNumero(v)} PAX`, '']} />
                <Legend
                  verticalAlign="bottom"
                  height={72}
                  iconType="circle"
                  wrapperStyle={{ fontSize: '11px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
          {totalPax > 0 && destino.length > 0 && (
            <p className="mt-2 text-center text-xs text-muted-foreground">
              {totalPax} PAX en total · {destino.length} destinos
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            🚁 Distribución por Transporte
          </CardTitle>
        </CardHeader>
        <CardContent>
          {transporte.length === 0 ? (
            <p className="py-16 text-center text-sm text-muted-foreground">
              Sin datos para graficar
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(130, transporte.length * 34 + 40)}>
              <BarChart data={transporte} layout="vertical" margin={{ top: 4, right: 44, left: 4, bottom: 4 }}>
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="nombre"
                  width={92}
                  tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  {...TOOLTIP_ESTILO}
                  formatter={(v) => {
                    const pax = aNumero(v)
                    const pct = totalPax > 0 ? ((pax / totalPax) * 100).toFixed(1) : '0'
                    return [`${pax} PAX (${pct}%)`, '']
                  }}
                />
                <Bar
                  dataKey="pax"
                  radius={[0, 4, 4, 0]}
                  barSize={18}
                  label={{
                    position: 'insideRight',
                    fill: '#fff',
                    fontSize: 11,
                    formatter: (v) => `  ${aNumero(v)}`,
                  }}
                >
                  {transporte.map((t) => (
                    <Cell key={t.nombre} fill={colorDeTransporte(t.nombre)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </>
  )
}
