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
import { companiasApi } from '@/lib/companias'
import { Trash2, Plus, Loader2, Building2 } from 'lucide-react'

interface CompaniaRecord {
  id?: string
  razon_social: string
  nombre_corto: string
}

export default function Companias() {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [razonSocial, setRazonSocial] = useState('')
  const [nombreCorto, setNombreCorto] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['companias'],
    queryFn: () => companiasApi.list(),
  })

  const companias = (data as CompaniaRecord[]) ?? []

  const createMutation = useMutation({
    mutationFn: () => companiasApi.create(razonSocial, nombreCorto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companias'] })
      setDialogOpen(false)
      setRazonSocial('')
      setNombreCorto('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (razonSocial: string) => companiasApi.delete(razonSocial),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companias'] })
    },
  })

  const columns: ColumnDef<CompaniaRecord>[] = useMemo(
    () => [
      {
        accessorKey: 'razon_social',
        header: 'Razón Social',
      },
      {
        accessorKey: 'nombre_corto',
        header: 'Nombre Corto',
      },
      {
        id: 'acciones',
        header: 'Acciones',
        cell: ({ row }) => {
          const rs = row.getValue('razon_social') as string
          return (
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:text-destructive"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate(rs)}
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
    data: companias,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (razonSocial && nombreCorto) {
      createMutation.mutate()
    }
  }

  return (
    <div className="flex flex-col space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Catálogo de Compañías</h1>
        <Button className="gap-2" onClick={() => setDialogOpen(true)}>
          <Plus className="h-4 w-4" />
          Agregar Compañía
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Compañías</CardTitle>
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
                ) : companias.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="h-40 text-center text-muted-foreground">
                      <div className="flex flex-col items-center gap-2">
                        <Building2 className="h-8 w-8" />
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
              <DialogTitle>Agregar Compañía</DialogTitle>
              <DialogDescription>
                Ingresa los datos de la nueva compañía
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="razonSocial">Razón Social</Label>
                <Input
                  id="razonSocial"
                  placeholder="Razón social de la compañía"
                  value={razonSocial}
                  onChange={(e) => setRazonSocial(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="nombreCorto">Nombre Corto</Label>
                <Input
                  id="nombreCorto"
                  placeholder="Nombre corto"
                  value={nombreCorto}
                  onChange={(e) => setNombreCorto(e.target.value)}
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
