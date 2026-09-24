import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { adminApi } from '@/lib/admin'
import type { Usuario } from '@/types'
import { Users, Shield } from 'lucide-react'

export default function AdminUsuarios() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'usuarios'],
    queryFn: () => adminApi.listUsers(),
  })

  const usuarios = (data as Usuario[]) ?? []

  const columns: ColumnDef<Usuario>[] = useMemo(
    () => [
      {
        accessorKey: 'nombre',
        header: 'Nombre',
      },
      {
        accessorKey: 'email',
        header: 'Email',
      },
      {
        accessorKey: 'admin',
        header: 'Admin',
        cell: ({ row }) => {
          const isAdmin = row.getValue('admin') as boolean
          return (
            <Badge variant={isAdmin ? 'success' : 'outline'}>
              {isAdmin ? 'Sí' : 'No'}
            </Badge>
          )
        },
      },
      {
        accessorKey: 'verificado',
        header: 'Verificado',
        cell: ({ row }) => {
          const isVerified = row.getValue('verificado') as boolean
          return (
            <Badge variant={isVerified ? 'success' : 'warning'}>
              {isVerified ? 'Sí' : 'No'}
            </Badge>
          )
        },
      },
      {
        accessorKey: 'created_at',
        header: 'Fecha de Registro',
        cell: ({ row }) => {
          const date = row.getValue('created_at') as string
          return new Date(date).toLocaleDateString()
        },
      },
    ],
    [],
  )

  const table = useReactTable({
    data: usuarios,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Shield className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-bold tracking-tight">Administración de Usuarios</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Usuarios</CardTitle>
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
                ) : usuarios.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="h-40 text-center text-muted-foreground">
                      <div className="flex flex-col items-center gap-2">
                        <Users className="h-8 w-8" />
                        No hay usuarios registrados
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
    </div>
  )
}
