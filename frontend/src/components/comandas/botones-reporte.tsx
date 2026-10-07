/**
 * Los botones de los cuatro reportes en bloque.
 *
 * Cada descarga descuenta una del contador del backend (decision D3), asi que
 * el boton se deshabilita mientras corre y se avisa cuando se acabaron. Nada
 * se descarga en automatico al abrir la pantalla, que es el problema que tenia
 * la app de Streamlit: ahi los cuatro `st.download_button(data=...)`
 * generaban los cuatro PDFs completos en CADA rerun, aunque nadie los pidiera
 * (app.py:1698-1728).
 */
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  BarChart3, FileText, Boxes, Ticket, Download, Loader2, Info,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { TipoReporte } from '@/types/comandas'

interface Props {
  tipos: TipoReporte[]
  onDescargar: (tipo: TipoReporte) => Promise<boolean>
  disabled: boolean
  /** Por que estan deshabilitados. Sin esto, los botones se ven pero nadie sabe por que. */
  motivoDeshabilitado?: string
}

const DEFINICION: Record<TipoReporte, { etiqueta: string; icono: LucideIcon; ayuda: string }> = {
  estadistico: {
    etiqueta: 'Reporte Estadístico',
    icono: BarChart3,
    ayuda: 'Resumen en una hoja: destino, transporte y compañías',
  },
  todas: {
    etiqueta: 'Todas las Comandas',
    icono: FileText,
    ayuda: 'Un PDF con todas, una por página, con el machote completo',
  },
  mortera: {
    etiqueta: 'Comandas c/ Mortera',
    icono: Boxes,
    ayuda: 'Otro diseño: las morteras con las 6 líneas de firma de control',
  },
  vales: {
    etiqueta: 'Vales de Alimentos',
    icono: Ticket,
    ayuda: '10 vales por hoja, con firma de recepción',
  },
}

/** El orden en que salen, igual que en la app de Streamlit. */
const ORDEN: TipoReporte[] = ['estadistico', 'todas', 'mortera', 'vales']

export function BotonesReporte({ tipos, onDescargar, disabled, motivoDeshabilitado }: Props) {
  const [descargando, setDescargando] = useState<TipoReporte | null>(null)

  async function manejar(tipo: TipoReporte) {
    if (descargando) return
    setDescargando(tipo)
    try {
      await onDescargar(tipo)
    } finally {
      setDescargando(null)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          📋 Gestión de Comandas
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/*
          Los botones se pintan SIEMPRE, incluso sin datos, deshabilitados y con
          el motivo a la vista.

          Antes solo aparecían cuando había comandas, y eso era peor que la app
          de Streamlit: esta al menos mostraba un `st.info` diciendo que no había
          datos. Ocultar el panel entero deja al usuario sin ningún indicio de
          que la función exista, y la conclusión que saca es "faltan los
          botones".
        */}
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {ORDEN.filter((t) => tipos.includes(t)).map((tipo) => {
            const { etiqueta, icono: Icono, ayuda } = DEFINICION[tipo]
            const cargando = descargando === tipo
            return (
              <Button
                key={tipo}
                variant="outline"
                className="h-auto flex-col items-start gap-1 py-2.5 text-left"
                disabled={disabled || !!descargando}
                title={disabled ? motivoDeshabilitado : ayuda}
                onClick={() => void manejar(tipo)}
              >
                <span className="flex w-full items-center gap-2 text-[13px] font-semibold">
                  {cargando
                    ? <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    : <Icono className="h-4 w-4 text-primary" />}
                  {etiqueta}
                  {!cargando && <Download className="ml-auto h-3.5 w-3.5 opacity-50" />}
                </span>
                <span className="text-[11px] font-normal leading-tight text-muted-foreground">
                  {ayuda}
                </span>
              </Button>
            )
          })}
        </div>

        {disabled && motivoDeshabilitado && (
          <p className="flex items-start gap-1.5 rounded-md border border-amber-500/30 bg-amber-500/10 px-2.5 py-2 text-xs text-amber-700 dark:text-amber-400">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            {motivoDeshabilitado}
          </p>
        )}

        <p className="text-[11px] leading-relaxed text-muted-foreground">
          Cada descarga cuenta como una descarga de tu plan, igual que el resto de la
          aplicación. Se genera el PDF al pedirlo, no al abrir la pantalla.
        </p>
      </CardContent>
    </Card>
  )
}
