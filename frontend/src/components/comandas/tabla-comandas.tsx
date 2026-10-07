/**
 * Tabla de comandas con TanStack Table.
 *
 * Sustituye al `st.dataframe` de la app de Streamlit, y agrega tres cosas que
 * ahi no habia: orden por columna, busqueda instantanea y el detalle de cada
 * comanda (las observaciones no se veian en pantalla; solo se imprimian en el
 * PDF).
 *
 * La busqueda usa `globalFilter` sobre folio, compania y destino, que es lo
 * que hacia la app (app.py:1751-1756).
 */
import { useMemo, useState } from 'react'
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { SortableHeader } from '@/components/ui/sortable-header'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Search, Download, FileText, Inbox } from 'lucide-react'
import type { Comanda } from '@/types/comandas'

interface Props {
  comandas: Comanda[]
  fecha: string
  /** Descarga el PDF de una comanda. Resuelve false si el usuario no pudo. */
  onDescargar: (folio: string) => Promise<boolean>
  /** El boton se deshabilita mientras corre una descarga. */
  descargando: string | null
}

export function TablaComandas({ comandas, onDescargar, descargando }: Props) {
  const [sorting, setSorting] = useState<SortingState>([{ id: 'comanda', desc: false }])
  const [busqueda, setBusqueda] = useState('')
  const [detalle, setDetalle] = useState<Comanda | null>(null)

  const columnas = useMemo<ColumnDef<Comanda>[]>(
    () => [
      {
        accessorKey: 'comanda',
        header: 'Folio',
        cell: ({ row }) => (
          <button
            type="button"
            onClick={() => setDetalle(row.original)}
            className="font-mono text-[13px] font-semibold text-primary hover:underline"
            title="Ver detalle"
          >
            {row.original.comanda}
          </button>
        ),
      },
      { accessorKey: 'horario', header: 'Horario' },
      {
        accessorKey: 'compania',
        header: 'Compañía',
        cell: ({ getValue }) => (
          <span className="block max-w-[220px] truncate" title={String(getValue())}>
            {String(getValue())}
          </span>
        ),
      },
      {
        accessorKey: 'destino',
        header: 'Destino',
        cell: ({ getValue }) => (
          <span className="block max-w-[140px] truncate" title={String(getValue())}>
            {String(getValue())}
          </span>
        ),
      },
      {
        accessorKey: 'pax',
        header: 'PAX',
        cell: ({ getValue }) => (
          <span className="tabular-nums font-semibold">{String(getValue())}</span>
        ),
      },
      { accessorKey: 'transporte', header: 'Transporte' },
      {
        accessorKey: 'menu_1',
        header: 'Menú 1',
        cell: ({ getValue }) => (
          <span className="tabular-nums text-muted-foreground">{String(getValue())}</span>
        ),
      },
      {
        accessorKey: 'menu_2',
        header: 'Menú 2',
        cell: ({ getValue }) => (
          <span className="tabular-nums text-muted-foreground">{String(getValue())}</span>
        ),
      },
      {
        accessorKey: 'tipo',
        header: 'Tipo',
        cell: ({ getValue }) => {
          const tipo = String(getValue())
          return tipo === 'MORTERA' ? (
            <Badge variant="secondary" className="bg-amber-500/15 text-amber-700 dark:text-amber-400">
              Mortera
            </Badge>
          ) : (
            <Badge variant="secondary" className="text-muted-foreground">Vianda</Badge>
          )
        },
      },
    ],
    [setDetalle],
  )

  const tabla = useReactTable({
    data: comandas,
    columns: columnas,
    state: { sorting, globalFilter: busqueda },
    onSortingChange: setSorting,
    onGlobalFilterChange: setBusqueda,
    globalFilterFn: (fila, _columna, valor) => {
      const texto = String(valor ?? '').toLowerCase().trim()
      if (!texto) return true
      const c = fila.original
      return (
        c.comanda.toLowerCase().includes(texto) ||
        c.compania.toLowerCase().includes(texto) ||
        c.destino.toLowerCase().includes(texto)
      )
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  const filas = tabla.getRowModel().rows
  const hayBusqueda = busqueda.trim().length > 0

  if (comandas.length === 0) return null

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder="Buscar por folio, destino o compañía…"
          className="pl-9"
        />
      </div>

      {filas.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-10 text-muted-foreground">
          <Inbox className="h-7 w-7 opacity-50" />
          <p className="text-sm">Sin resultados para «{busqueda}»</p>
        </div>
      ) : (
        <>
          <div className="max-h-[420px] overflow-auto rounded-lg border border-border/60">
            <Table>
              <TableHeader className="sticky top-0 z-10 bg-card">
                {tabla.getHeaderGroups().map((grupo) => (
                  <TableRow key={grupo.id} className="hover:bg-transparent">
                    {grupo.headers.map((h) => (
                      <TableHead key={h.id} className="h-10 px-3">
                        <SortableHeader header={h}>
                          {flexRender(h.column.columnDef.header, h.getContext())}
                        </SortableHeader>
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {filas.map((fila) => (
                  <TableRow
                    key={fila.id}
                    onClick={() => setDetalle(fila.original)}
                    className="cursor-pointer"
                  >
                    {fila.getVisibleCells().map((celda) => (
                      <TableCell key={celda.id} className="px-3 py-2.5 text-[13px]">
                        {flexRender(celda.column.columnDef.cell, celda.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <p className="text-xs text-muted-foreground">
            {hayBusqueda
              ? `${filas.length} de ${comandas.length} comandas`
              : `${comandas.length} comandas · clic en una fila para ver el detalle`}
          </p>
        </>
      )}

      <Dialog open={!!detalle} onOpenChange={(abierto) => !abierto && setDetalle(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 font-mono">
              <FileText className="h-4 w-4 text-primary" />
              {detalle?.comanda}
            </DialogTitle>
            <DialogDescription>
              {detalle?.compania} → {detalle?.destino}
            </DialogDescription>
          </DialogHeader>

          {detalle && (
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <dt className="text-muted-foreground">Horario</dt>
              <dd className="font-mono">{detalle.horario}</dd>

              <dt className="text-muted-foreground">Personas</dt>
              <dd className="tabular-nums font-semibold">{detalle.pax}</dd>

              <dt className="text-muted-foreground">Transporte</dt>
              <dd>{detalle.transporte}</dd>

              <dt className="text-muted-foreground">Menú 1</dt>
              <dd className="tabular-nums">{detalle.menu_1}</dd>

              <dt className="text-muted-foreground">Menú 2</dt>
              <dd className="tabular-nums">{detalle.menu_2}</dd>

              <dt className="text-muted-foreground">Tipo</dt>
              <dd>
                {detalle.tipo === 'MORTERA'
                  ? 'Mortera (6 firmas extra en el PDF)'
                  : 'Vianda'}
              </dd>
            </dl>
          )}

          {detalle?.observaciones && (
            <div className="rounded-md border border-border/60 bg-muted/40 p-3">
              <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Observaciones
              </p>
              <p className="text-sm leading-relaxed">{detalle.observaciones}</p>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setDetalle(null)}>Cerrar</Button>
            {detalle && (
              <Button
                className="gap-2"
                disabled={descargando === detalle.comanda}
                onClick={() => void onDescargar(detalle.comanda)}
              >
                {descargando === detalle.comanda
                  ? <Download className="h-4 w-4 animate-pulse" />
                  : <Download className="h-4 w-4" />}
                Descargar PDF
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
