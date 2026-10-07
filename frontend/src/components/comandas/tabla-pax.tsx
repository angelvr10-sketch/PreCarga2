/**
 * Las dos tablas de la izquierda del dashboard: PAX por destino y PAX por
 * compañía. Ordenadas de mayor a menor.
 *
 * Equivalen a los dos `st.dataframe` de la app de Streamlit (app.py:1616 y
 * 1622), con la diferencia de que aqui el texto largo se recorta con
 * `truncate` en vez de a 30 caracteres por la fuerza.
 */
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { aFilas } from '@/lib/comandas'

interface Props {
  titulo: string
  icono: string
  conteo: Record<string, number>
  /** Limite de filas antes de resumir con "y N mas". */
  maximo?: number
  total: number
}

export function TablaPax({ titulo, icono, conteo, maximo = 12, total }: Props) {
  const filas = aFilas(conteo)
  const visibles = filas.slice(0, maximo)
  const resto = filas.length - visibles.length

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          {icono} {titulo}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 px-0 pb-0">
        {filas.length === 0 ? (
          <p className="px-6 py-10 text-center text-sm text-muted-foreground">Sin datos</p>
        ) : (
          <>
            <div className="max-h-[264px] overflow-auto">
              <Table>
                <TableHeader className="sticky top-0 z-10 bg-card">
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="h-9 px-4 text-[11px] uppercase tracking-wide text-muted-foreground">
                      Nombre
                    </TableHead>
                    <TableHead className="h-9 px-4 text-right text-[11px] uppercase tracking-wide text-muted-foreground">
                      PAX
                    </TableHead>
                    <TableHead className="h-9 w-20 px-2 text-right text-[11px] uppercase tracking-wide text-muted-foreground">
                      %
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visibles.map((f) => (
                    <TableRow key={f.nombre}>
                      <TableCell
                        className="max-w-[190px] truncate px-4 py-1.5 text-[13px]"
                        title={f.nombre}
                      >
                        {f.nombre}
                      </TableCell>
                      <TableCell className="px-4 py-1.5 text-right text-[13px] font-semibold tabular-nums">
                        {f.pax}
                      </TableCell>
                      <TableCell className="px-2 py-1.5 text-right text-[12px] tabular-nums text-muted-foreground">
                        {total > 0 ? ((f.pax / total) * 100).toFixed(1) : '0.0'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            {resto > 0 && (
              <p className="border-t border-border/50 px-4 py-1.5 text-[11px] text-muted-foreground">
                y {resto} {resto === 1 ? 'más' : 'más'}
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
