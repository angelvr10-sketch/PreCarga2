import { useState, useMemo, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from '@tanstack/react-table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { SortableHeader } from '@/components/ui/sortable-header'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { solicitudesApi } from '@/lib/solicitudes'
import type { Solicitud } from '@/types'
import { Search, Download, FileText, Loader2, CheckCircle2, XCircle, ChevronLeft, ChevronRight } from 'lucide-react'

export default function Altas() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [page, setPage] = useState(1)
  const [sorting, setSorting] = useState<SortingState>([{ id: 'created_at', desc: true }])
  const [rowSelection, setRowSelection] = useState({})
  const [dialogOpen, setDialogOpen] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedSearch(search)
      setPage(1)
    }, 350)
    return () => clearTimeout(t)
  }, [search])

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['solicitudes', debouncedSearch, page],
    queryFn: () => solicitudesApi.list(page, debouncedSearch),
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  })

  const mutation = useMutation({
    mutationFn: (ids: string[]) => solicitudesApi.generarEntradas(ids),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['solicitudes'] })
      setRowSelection({})
      const url = data.download_url ?? (data.archivo ? `/api/descargar/${data.archivo}` : '')
      if (url) {
        const a = document.createElement('a')
        a.href = url
        a.download = ''
        document.body.appendChild(a)
        a.click()
        a.remove()
      }
    },
  })

  const solicitudes = data?.solicitudes ?? []
  const totalPages = data?.total_pages ?? 1

  const selectedIds = useMemo(() => {
    return Object.keys(rowSelection)
      .map((idx) => solicitudes[Number(idx)]?.folio)
      .filter(Boolean) as string[]
  }, [rowSelection, solicitudes])

  const columns: ColumnDef<Solicitud>[] = useMemo(
    () => [
      {
        id: 'select',
        header: ({ table }) => (
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-gray-300"
            checked={table.getIsAllPageRowsSelected()}
            onChange={(e) => table.toggleAllPageRowsSelected(!!e.target.checked)}
          />
        ),
        cell: ({ row }) => (
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-gray-300"
            checked={row.getIsSelected()}
            onChange={(e) => row.toggleSelected(!!e.target.checked)}
          />
        ),
        enableSorting: false,
      },
      {
        accessorKey: 'folio',
        header: ({ header }) => <SortableHeader header={header}>N° Solicitud</SortableHeader>,
        cell: ({ row }) => <span className="font-medium">{row.getValue('folio')}</span>,
      },
      {
        accessorKey: 'created_at',
        header: ({ header }) => <SortableHeader header={header}>Fecha de Llegada</SortableHeader>,
        cell: ({ row }) => {
          const fecha = row.getValue('created_at') as string
          return fecha ? new Date(fecha).toLocaleDateString() : <span className="text-muted-foreground">—</span>
        },
      },
      {
        accessorKey: 'destino',
        header: ({ header }) => <SortableHeader header={header}>Destino</SortableHeader>,
        cell: ({ row }) => {
          const destino = row.getValue('destino') as string
          if (!destino) return <span className="text-muted-foreground">—</span>
          const cls =
            destino.toUpperCase() === 'CPZ'
              ? 'bg-sky-500/15 text-sky-300'
              : destino.toUpperCase() === 'RPX'
                ? 'bg-violet-500/15 text-violet-300'
                : 'bg-muted text-muted-foreground'
          return (
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${cls}`}>
              {destino}
            </span>
          )
        },
      },
      {
        accessorKey: 'compania',
        header: ({ header }) => <SortableHeader header={header}>Compañía</SortableHeader>,
        cell: ({ row }) => {
          const value = row.getValue('compania') as string
          return value || <span className="text-muted-foreground">—</span>
        },
      },
      {
        accessorKey: 'personal_count',
        header: ({ header }) => <SortableHeader header={header} className="justify-end">Suben</SortableHeader>,
        cell: ({ row }) => (
          <span className="flex justify-end font-semibold text-emerald-400">
            {row.getValue('personal_count') ?? 0}
          </span>
        ),
      },
      {
        accessorKey: 'bajas_count',
        header: ({ header }) => <SortableHeader header={header} className="justify-end">Bajan</SortableHeader>,
        cell: ({ row }) => (
          <span className="flex justify-end font-semibold text-destructive">
            {row.getValue('bajas_count') ?? 0}
          </span>
        ),
      },
      {
        id: 'acciones',
        header: 'Descargar',
        enableSorting: false,
        cell: ({ row }) => {
          const folio = row.getValue('folio') as string
          return (
            <Button variant="outline" size="sm" className="gap-2" asChild>
              <a href={`/api/descargar/${folio}.xlsx`} target="_blank" rel="noreferrer">
                <Download className="h-4 w-4" />
              </a>
            </Button>
          )
        },
      },
    ],
    [],
  )

  const table = useReactTable({
    data: solicitudes,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    state: { sorting, rowSelection },
    onSortingChange: setSorting,
    onRowSelectionChange: setRowSelection,
    enableRowSelection: true,
  })

  const handleGenerate = () => {
    mutation.mutate(selectedIds)
  }

  return (
    <div className="flex flex-col space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Altas</h1>
        {selectedIds.length > 0 && (
          <Button className="gap-2" onClick={() => setDialogOpen(true)}>
            <FileText className="h-4 w-4" />
            Generar Entradas ({selectedIds.length})
          </Button>
        )}
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Buscar solicitudes..."
          className="pl-10"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Solicitudes</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="flex-1 overflow-auto">
            <Table>
              <TableHeader>
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <TableHead key={header.id}>
                        {header.isPlaceholder
                          ? null
                          : flexRender(header.column.columnDef.header, header.getContext())}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {isError ? (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="h-40 text-center">
                      <div className="flex flex-col items-center justify-center gap-3">
                        <p className="text-muted-foreground">Error al cargar las solicitudes</p>
                        <Button variant="outline" size="sm" onClick={() => refetch()}>
                          Reintentar
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : isLoading ? (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="h-40 text-center text-muted-foreground">
                      <div className="flex items-center justify-center gap-2">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                        Cargando...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : solicitudes.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="h-40 text-center text-muted-foreground">
                      No se encontraron solicitudes
                    </TableCell>
                  </TableRow>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <TableRow key={row.id} data-state={row.getIsSelected() && 'selected'}>
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id}>
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Página {page} de {totalPages}
        </p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            <ChevronLeft className="h-4 w-4" />
            Anterior
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            Siguiente
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generar Entradas</DialogTitle>
            <DialogDescription>
              Se generarán entradas para {selectedIds.length} solicitud{selectedIds.length !== 1 ? 'es' : ''} seleccionada{selectedIds.length !== 1 ? 's' : ''}.
            </DialogDescription>
          </DialogHeader>

          {mutation.isError && (
            <div className="flex items-center gap-3 rounded-lg border border-destructive/50 p-4">
              <XCircle className="h-5 w-5 shrink-0 text-destructive" />
              <p className="text-sm text-destructive">
                {mutation.error instanceof Error ? mutation.error.message : 'Error al generar entradas'}
              </p>
            </div>
          )}

          {mutation.data && (
            <div className="flex items-center gap-3 rounded-lg border border-emerald-500/50 p-4">
              <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
              <p className="text-sm text-emerald-400">
                {mutation.data.registros} registros generados exitosamente. El archivo se descargó automáticamente.
              </p>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => { setDialogOpen(false); mutation.reset() }}>
              Cerrar
            </Button>
            <Button
              className="gap-2"
              disabled={mutation.isPending || !!mutation.data}
              onClick={handleGenerate}
            >
              {mutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileText className="h-4 w-4" />
              )}
              {mutation.isPending ? 'Generando...' : 'Confirmar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}