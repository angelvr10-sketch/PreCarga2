import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { activosApi } from '@/lib/activos'
import { Trash2, Plus, Loader2, Package } from 'lucide-react'

interface ActivoRecord {
  id?: string
  nombre: string
}

export default function Activos() {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [nombre, setNombre] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['activos'],
    queryFn: () => activosApi.list(),
  })

  const activos = (data as ActivoRecord[]) ?? []

  const createMutation = useMutation({
    mutationFn: () => activosApi.create(nombre),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activos'] })
      setDialogOpen(false)
      setNombre('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (nombre: string) => activosApi.delete(nombre),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activos'] })
    },
  })

  const columns: ColumnDef<ActivoRecord>[] = useMemo(
    () => [
      {
        accessorKey: 'nombre',
        header: 'Nombre',
      },
      {
        id: 'acciones',
        header: 'Acciones',
        cell: ({ row }) => {
          const name = row.getValue('nombre') as string
          return (
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:text-destructive"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate(name)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )
        },
      },
    ],
    [deleteMutation.isPending],
  )

  const table = useReactTable({
    data: activos,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (nombre) {
      createMutation.mutate()
    }
  }

  return (
    <div className="flex flex-col space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Catálogo de Activos</h1>
        <Button className="gap-2" onClick={() => setDialogOpen(true)}>
          <Plus className="h-4 w-4" />
          Agregar Activo
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Activos</CardTitle>
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
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="h-40 text-center text-muted-foreground">
                      <div className="flex items-center justify-center gap-2">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                        Cargando...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : activos.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="h-40 text-center text-muted-foreground">
                      <div className="flex flex-col items-center gap-2">
                        <Package className="h-8 w-8" />
                        No hay registros
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <TableRow key={row.id}>
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

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <form onSubmit={handleSubmit}>
            <DialogHeader>
              <DialogTitle>Agregar Activo</DialogTitle>
              <DialogDescription>
                Ingresa el nombre del nuevo activo
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="nombre">Nombre</Label>
                <Input
                  id="nombre"
                  placeholder="Nombre del activo"
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                  required
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" type="button" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button className="gap-2" type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                {createMutation.isPending ? 'Guardando...' : 'Guardar'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
