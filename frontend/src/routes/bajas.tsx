import { useState, useRef, useMemo } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { solicitudesApi } from '@/lib/solicitudes'
import { bajasApi } from '@/lib/bajas'
import type { Solicitud } from '@/types'
import { Upload, Database, Search, Download, Loader2, CheckCircle2, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function Bajas() {
  const [step, setStep] = useState<'upload' | 'search'>('upload')
  const [bdToken, setBdToken] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const [rowSelection, setRowSelection] = useState({})
  const [search, setSearch] = useState('')

  const { data: solicitudesData } = useQuery({
    queryKey: ['solicitudes', search, 1],
    queryFn: () => solicitudesApi.list(1, search),
    enabled: step === 'search',
  })

  const uploadMutation = useMutation({
    mutationFn: (f: File) => bajasApi.cargarBd(f),
    onSuccess: (data) => {
      setBdToken(data.token)
      setStep('search')
    },
  })

  const buscarMutation = useMutation({
    mutationFn: ({ solicitudes, token }: { solicitudes: string[]; token: string }) =>
      bajasApi.buscarBajas(solicitudes, token),
  })

  const solicitudes = solicitudesData?.solicitudes ?? []

  const selectedSolicitudes = useMemo(() => {
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
        header: 'Folio',
      },
      {
        accessorKey: 'tipo',
        header: 'Tipo',
        cell: ({ row }) => <span className="capitalize">{row.getValue('tipo')}</span>,
      },
      {
        accessorKey: 'personal_count',
        header: 'Personal',
        cell: ({ row }) => row.getValue('personal_count') ?? 'N/A',
      },
      {
        accessorKey: 'created_at',
        header: 'Fecha',
        cell: ({ row }) => new Date(row.getValue('created_at')).toLocaleDateString(),
      },
    ],
    [],
  )

  const table = useReactTable({
    data: solicitudes,
    columns,
    getCoreRowModel: getCoreRowModel(),
    state: { rowSelection },
    onRowSelectionChange: setRowSelection,
    enableRowSelection: true,
  })

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = () => {
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      setFile(droppedFile)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected) {
      setFile(selected)
    }
  }

  const handleUpload = () => {
    if (file) {
      uploadMutation.mutate(file)
    }
  }

  const handleBuscarBajas = () => {
    if (bdToken && selectedSolicitudes.length > 0) {
      buscarMutation.mutate({ solicitudes: selectedSolicitudes, token: bdToken })
    }
  }

  const result = buscarMutation.data

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Bajas</h1>

      {step === 'upload' && (
        <Card>
          <CardHeader>
            <CardTitle>Subir Base de Datos</CardTitle>
            <CardDescription>
              Selecciona o arrastra un archivo CSV o XLSX con la base de datos de personal
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div
              className={cn(
                'flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 transition-colors',
                isDragOver
                  ? 'border-primary bg-primary/5'
                  : 'border-muted-foreground/25 hover:border-muted-foreground/50',
              )}
              onClick={() => inputRef.current?.click()}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <Database className="mb-4 h-12 w-12 text-muted-foreground" />
              {file ? (
                <p className="text-sm font-medium">{file.name}</p>
              ) : (
                <>
                  <p className="mb-1 text-sm font-medium">
                    Arrastra un archivo aquí o haz clic para seleccionar
                  </p>
                  <p className="text-xs text-muted-foreground">CSV o XLSX</p>
                </>
              )}
            </div>

            <input
              ref={inputRef}
              type="file"
              accept=".csv,.xlsx"
              className="hidden"
              onChange={handleFileSelect}
            />

            {uploadMutation.isError && (
              <div className="flex items-center gap-3 rounded-lg border border-destructive/50 p-4">
                <XCircle className="h-5 w-5 shrink-0 text-destructive" />
                <p className="text-sm text-destructive">
                  {uploadMutation.error instanceof Error ? uploadMutation.error.message : 'Error al cargar archivo'}
                </p>
              </div>
            )}

            {uploadMutation.data && (
              <div className="flex items-center gap-3 rounded-lg border border-emerald-500/50 p-4">
                <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
                <p className="text-sm text-emerald-400">
                  Base de datos cargada: {uploadMutation.data.columnas} columnas detectadas
                </p>
              </div>
            )}

            <Button
              className="w-full gap-2"
              disabled={!file || uploadMutation.isPending}
              onClick={handleUpload}
            >
              {uploadMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              {uploadMutation.isPending ? 'Cargando...' : 'Cargar Base de Datos'}
            </Button>
          </CardContent>
        </Card>
      )}

      {step === 'search' && (
        <>
          <div className="flex items-center justify-between">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar solicitudes..."
                className="pl-10"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Button
              className="gap-2"
              disabled={selectedSolicitudes.length === 0 || buscarMutation.isPending}
              onClick={handleBuscarBajas}
            >
              {buscarMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              Buscar Bajas ({selectedSolicitudes.length})
            </Button>
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
                    {solicitudes.length === 0 ? (
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

          {buscarMutation.isPending && (
            <Card>
              <CardContent className="flex items-center justify-center gap-3 py-8">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">Buscando bajas en la base de datos...</p>
              </CardContent>
            </Card>
          )}

          {buscarMutation.isError && (
            <Card className="border-destructive/50">
              <CardContent className="flex items-center gap-3 py-6">
                <XCircle className="h-6 w-6 shrink-0 text-destructive" />
                <div className="flex-1">
                  <p className="font-medium text-destructive">Error</p>
                  <p className="text-sm text-muted-foreground">
                    {buscarMutation.error instanceof Error ? buscarMutation.error.message : 'Error al buscar bajas'}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {result && result.ok && (
            <Card className="border-emerald-500/50">
              <CardContent className="space-y-4 py-6">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="h-6 w-6 shrink-0 text-emerald-400" />
                  <div>
                    <p className="font-medium text-emerald-400">Bajas encontradas</p>
                    <p className="text-sm text-muted-foreground">
                      {result.encontrados} registro{result.encontrados !== 1 ? 's' : ''} encontrado{result.encontrados !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>
                {result.archivo && (
                  <Button variant="outline" className="w-full gap-2" asChild>
                    <a href={`/api/descargar/${result.archivo}`}>
                      <Download className="h-4 w-4" />
                      Descargar resultados
                    </a>
                  </Button>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
