/**
 * Las seis tarjetas de resumen.
 *
 * Mismos numeros, colores y emojis que tenian en la app de Streamlit
 * (app.py:1588-1595), para que quien ya usaba la app recognize la pantalla.
 */
import type { Estadisticas } from '@/types/comandas'
import { cn } from '@/lib/utils'

interface Props {
  stats: Estadisticas
}

export function KpiGrid({ stats }: Props) {
  const tarjetas = [
    { icono: '📋', valor: stats.total_comandas, etiqueta: 'Comandas', color: 'text-blue-500' },
    { icono: '👥', valor: stats.total_alimentos, etiqueta: 'Total PAX', color: 'text-emerald-500' },
    { icono: '🍱', valor: stats.total_menu1, etiqueta: 'Menú 1', color: 'text-violet-500' },
    { icono: '🍲', valor: stats.total_menu2, etiqueta: 'Menú 2', color: 'text-amber-500' },
    { icono: '🥘', valor: stats.total_mortera, etiqueta: 'Morteras', color: 'text-teal-500' },
    { icono: '🥡', valor: stats.total_viandas, etiqueta: 'Viandas', color: 'text-red-500' },
  ]

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      {tarjetas.map((t) => (
        <div
          key={t.etiqueta}
          className={cn(
            'group relative overflow-hidden rounded-xl border border-border/60 bg-card p-4 text-center',
            'transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md',
          )}
        >
          {/* Halo del color de la tarjeta, como el .kpi-glow de la app. */}
          <div
            aria-hidden
            className="absolute -top-8 left-1/2 h-20 w-20 -translate-x-1/2 rounded-full opacity-20 blur-2xl transition-opacity group-hover:opacity-35"
            style={{ backgroundColor: 'currentColor' }}
          />
          <div className="relative text-2xl" aria-hidden>{t.icono}</div>
          <div className={cn('relative mt-1 text-2xl font-extrabold leading-tight tabular-nums', t.color)}>
            {t.valor}
          </div>
          <div className="relative mt-0.5 text-[11px] uppercase tracking-wider text-muted-foreground">
            {t.etiqueta}
          </div>
        </div>
      ))}
    </div>
  )
}
