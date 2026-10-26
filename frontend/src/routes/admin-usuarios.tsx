import { useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  type ColumnDef,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { SortableHeader } from '@/components/ui/sortable-header'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { adminApi, type AdminUser, type Rol } from '@/lib/admin'
import { useAuth } from '@/hooks/use-auth'
import { notificar } from '@/hooks/use-toast'
import { cn, fechaLocal, formatFecha } from '@/lib/utils'
import {
  AlertCircle,
  BadgeCheck,
  CalendarPlus,
  CalendarX,
  KeyRound,
  Loader2,
  Power,
  PowerOff,
  Plus,
  Search,
  Shield,
  Trash2,
  UserCheck,
  Users,
} from 'lucide-react'

const ROLES: Array<{ value: Rol; label: string }> = [
  { value: 'admin', label: 'Administrador' },
  { value: 'usuario', label: 'Usuario' },
  { value: 'lector', label: 'Lector' },
]

const ROL_LABEL: Record<Rol, string> = {
  admin: 'Administrador',
  usuario: 'Usuario',
  lector: 'Lector',
}

const selectClass =
  'h-8 rounded-md border border-[rgb(255_255_255_/_0.10)] bg-[rgb(255_255_255_/_0.04)] ' +
  'px-2 text-[13px] text-foreground outline-none transition-colors ' +
  'hover:border-[rgb(255_255_255_/_0.16)] focus:border-primary focus:ring-2 focus:ring-primary/30 ' +
  'disabled:cursor-not-allowed disabled:opacity-40'

function diasRestantes(expira: string | null | undefined): number | null {
  const fecha = fechaLocal(expira)
  if (!fecha) return null
  const hoy = new Date()
  hoy.setHours(0, 0, 0, 0)
  return Math.round((fecha.getTime() - hoy.getTime()) / 86_400_000)
}

function iniciales(nombre: string): string {
  const partes = nombre.trim().split(/\s+/).filter(Boolean)
  if (partes.length === 0) return '?'
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase()
  return (partes[0][0] + partes[1][0]).toUpperCase()
}

function mensajeError(error: unknown): string {
  return error instanceof Error ? error.message : 'Intenta de nuevo'
}

export default function AdminUsuarios() {
  const queryClient = useQueryClient()
  const { user: sesion } = useAuth()

  const [busqueda, setBusqueda] = useState('')
  const [filtroRol, setFiltroRol] = useState<'todos' | Rol>('todos')
  const [filtroEstado, setFiltroEstado] = useState<'todos' | 'activos' | 'inactivos'>('todos')
  const [sorting, setSorting] = useState<SortingState>([{ id: 'created_at', desc: true }])

  const [crearOpen, setCrearOpen] = useState(false)
  const [nuevoNombre, setNuevoNombre] = useState('')
  const [nuevoEmail, setNuevoEmail] = useState('')
  const [nuevoPassword, setNuevoPassword] = useState('')
  const [nuevoRol, setNuevoRol] = useState<Rol>('usuario')
  const [nuevosDias, setNuevosDias] = useState('0')

  const [passwordUser, setPasswordUser] = useState<AdminUser | null>(null)
  const [passwordNueva, setPasswordNueva] = useState('')
  const [passwordConfirmar, setPasswordConfirmar] = useState('')

  const [extenderUser, setExtenderUser] = useState<AdminUser | null>(null)
  const [extenderDias, setExtenderDias] = useState('30')

  const [eliminarUser, setEliminarUser] = useState<AdminUser | null>(null)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'usuarios'],
    queryFn: () => adminApi.listUsers(),
  })

  const usuarios = useMemo(() => (data as AdminUser[] | undefined) ?? [], [data])

  const invalidar = () => queryClient.invalidateQueries({ queryKey: ['admin', 'usuarios'] })

  const crearMutation = useMutation({
    mutationFn: (dias: number) =>
      adminApi.createUser({
        nombre: nuevoNombre,
        email: nuevoEmail,
        password: nuevoPassword,
        rol: nuevoRol,
        dias,
      }),
    onSuccess: (res) => {
      invalidar()
      setCrearOpen(false)
      setNuevoNombre('')
      setNuevoEmail('')
      setNuevoPassword('')
      setNuevoRol('usuario')
      setNuevosDias('0')
      notificar('Usuario creado', res.mensaje || 'La cuenta ya puede iniciar sesión.', 'exito')
    },
    onError: (error) => notificar('No se pudo crear el usuario', mensajeError(error), 'error'),
  })

  const actualizarMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof adminApi.updateUser>[1] }) =>
      adminApi.updateUser(id, data),
    onSuccess: () => invalidar(),
    onError: (error) => notificar('No se pudo actualizar', mensajeError(error), 'error'),
  })

  const eliminarMutation = useMutation({
    mutationFn: (id: string) => adminApi.deleteUser(id),
    onSuccess: () => {
      invalidar()
      setEliminarUser(null)
      notificar('Usuario eliminado', 'La cuenta y sus sesiones se borraron.', 'exito')
    },
    onError: (error) => notificar('No se pudo eliminar', mensajeError(error), 'error'),
  })

  const cambioRol = (usuario: AdminUser, rol: Rol) => {
    if (rol === usuario.rol) return
    actualizarMutation.mutate(
      { id: usuario.id, data: { rol } },
      { onSuccess: () => notificar('Rol actualizado', `${usuario.nombre}: ${ROL_LABEL[rol]}`, 'exito') },
    )
  }

  const alternarActivo = (usuario: AdminUser) => {
    const activo = !usuario.activo
    actualizarMutation.mutate(
      { id: usuario.id, data: { activo } },
      {
        onSuccess: () =>
          notificar(
            activo ? 'Usuario activado' : 'Usuario desactivado',
            activo ? `${usuario.nombre} puede volver a entrar.` : `${usuario.nombre} ya no puede iniciar sesión.`,
            'exito',
          ),
      },
    )
  }

  const verificar = (usuario: AdminUser) => {
    actualizarMutation.mutate(
      { id: usuario.id, data: { verificado: true } },
      { onSuccess: () => notificar('Correo verificado', usuario.email || usuario.nombre, 'exito') },
    )
  }

  const filtrados = useMemo(() => {
    const q = busqueda.trim().toLowerCase()
    return usuarios.filter((u) => {
      if (filtroRol !== 'todos' && u.rol !== filtroRol) return false
      if (filtroEstado === 'activos' && u.activo === false) return false
      if (filtroEstado === 'inactivos' && u.activo !== false) return false
      if (!q) return true
      return (
        u.nombre.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q) ||
        ROL_LABEL[u.rol].toLowerCase().includes(q)
      )
    })
  }, [usuarios, busqueda, filtroRol, filtroEstado])

  const kpis = useMemo(() => {
    const inactivosOSinSuscripcion = usuarios.filter((u) => {
      const dias = diasRestantes(u.expira)
      return dias === null || dias < 0
    }).length
    return {
      total: usuarios.length,
      activos: usuarios.filter((u) => u.activo !== false).length,
      admins: usuarios.filter((u) => u.rol === 'admin').length,
      sinSuscripcion: inactivosOSinSuscripcion,
    }
  }, [usuarios])

  const columnas: ColumnDef<AdminUser>[] = useMemo(
    () => [
      {
        accessorKey: 'nombre',
        header: ({ header }) => <SortableHeader header={header}>Usuario</SortableHeader>,
        cell: ({ row }) => {
          const u = row.original
          return (
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-[11px] font-semibold text-primary">
                {iniciales(u.nombre)}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="truncate font-medium">{u.nombre || '—'}</span>
                  {sesion?.id === u.id && <Badge variant="accent">Tú</Badge>}
                </div>
                <div className="truncate text-xs text-muted-foreground">{u.email || 'Sin correo'}</div>
              </div>
            </div>
          )
        },
      },
      {
        accessorKey: 'rol',
        header: ({ header }) => <SortableHeader header={header}>Rol</SortableHeader>,
        cell: ({ row }) => {
          const u = row.original
          const esUnoMismo = sesion?.id === u.id
          return (
            <select
              className={selectClass}
              value={u.rol}
              disabled={actualizarMutation.isPending || esUnoMismo}
              title={esUnoMismo ? 'No puedes cambiar tu propio rol' : 'Cambiar rol'}
              onChange={(e) => cambioRol(u, e.target.value as Rol)}
            >
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          )
        },
      },
      {
        accessorKey: 'activo',
        header: ({ header }) => <SortableHeader header={header}>Estado</SortableHeader>,
        cell: ({ row }) => {
          const u = row.original
          return (
            <div className="flex flex-wrap items-center gap-1">
              <Badge variant={u.activo === false ? 'destructive' : 'success'}>
                {u.activo === false ? 'Inactivo' : 'Activo'}
              </Badge>
              <Badge variant={u.verificado ? 'success' : 'warning'}>
                {u.verificado ? 'Verificado' : 'Sin verificar'}
              </Badge>
            </div>
          )
        },
      },
      {
        accessorKey: 'expira',
        header: ({ header }) => <SortableHeader header={header}>Suscripción</SortableHeader>,
        sortingFn: (a, b) => {
          const fa = fechaLocal(a.original.expira)?.getTime() ?? 0
          const fb = fechaLocal(b.original.expira)?.getTime() ?? 0
          return fa - fb
        },
        cell: ({ row }) => {
          const dias = diasRestantes(row.original.expira)
          if (dias === null) return <span className="text-xs text-muted-foreground">Sin suscripción</span>
          if (dias < 0) {
            return (
              <Badge variant="destructive" title={`Venció el ${formatFecha(row.original.expira)}`}>
                Vencida
              </Badge>
            )
          }
          return (
            <div className="flex flex-col gap-0.5">
              <Badge variant={dias <= 7 ? 'warning' : 'success'}>
                {dias === 0 ? 'Vence hoy' : `${dias} día${dias === 1 ? '' : 's'}`}
              </Badge>
              <span className="text-[11px] text-muted-foreground">{formatFecha(row.original.expira)}</span>
            </div>
          )
        },
      },
      {
        accessorKey: 'created_at',
        header: ({ header }) => <SortableHeader header={header}>Registro</SortableHeader>,
        cell: ({ row }) => (
          <span className="text-xs text-muted-foreground">{formatFecha(row.original.created_at) || '—'}</span>
        ),
      },
      {
        id: 'acciones',
        header: () => <span className="sr-only">Acciones</span>,
        cell: ({ row }) => {
          const u = row.original
          const esUnoMismo = sesion?.id === u.id
          const ocupado = actualizarMutation.isPending || eliminarMutation.isPending
          return (
            <div className="flex items-center justify-end gap-0.5">
              {!u.verificado && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  title="Marcar correo como verificado"
                  disabled={ocupado}
                  onClick={() => verificar(u)}
                >
                  <BadgeCheck className="h-4 w-4" />
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon-sm"
                title={u.activo === false ? 'Activar usuario' : 'Desactivar usuario'}
                disabled={ocupado || esUnoMismo}
                onClick={() => alternarActivo(u)}
              >
                {u.activo === false ? <Power className="h-4 w-4" /> : <PowerOff className="h-4 w-4" />}
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                title="Restablecer contraseña"
                disabled={ocupado}
                onClick={() => {
                  setPasswordUser(u)
                  setPasswordNueva('')
                  setPasswordConfirmar('')
                }}
              >
                <KeyRound className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                title="Extender suscripción"
                disabled={ocupado}
                onClick={() => {
                  setExtenderUser(u)
                  setExtenderDias('30')
                }}
              >
                <CalendarPlus className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                className="text-destructive hover:text-destructive"
                title={esUnoMismo ? 'No puedes eliminar tu propia cuenta' : 'Eliminar usuario'}
                disabled={ocupado || esUnoMismo}
                onClick={() => setEliminarUser(u)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          )
        },
      },
    ],
    [sesion?.id, actualizarMutation.isPending, eliminarMutation.isPending],
  )

  const table = useReactTable({
    data: filtrados,
    columns: columnas,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 10 } },
  })

  const errorCrear = crearMutation.error ? mensajeError(crearMutation.error) : null
  const errorPassword =
    passwordNueva.length > 0 && passwordNueva !== passwordConfirmar
      ? 'Las contraseñas no coinciden'
      : null

  const guardarPassword = (e: FormEvent) => {
    e.preventDefault()
    if (!passwordUser) return
    if (passwordNueva.length < 6) {
      notificar('Contraseña demasiado corta', 'Usa al menos 6 caracteres.', 'aviso')
      return
    }
    if (passwordNueva !== passwordConfirmar) return
    actualizarMutation.mutate(
      { id: passwordUser.id, data: { password: passwordNueva } },
      {
        onSuccess: () => {
          setPasswordUser(null)
          notificar('Contraseña actualizada', `Se cambió la contraseña de ${passwordUser.nombre}.`, 'exito')
        },
      },
    )
  }

  const guardarExtension = (e: FormEvent) => {
    e.preventDefault()
    if (!extenderUser) return
    const dias = Number(extenderDias)
    if (!Number.isInteger(dias) || dias <= 0) {
      notificar('Días inválidos', 'Ingresa un número entero mayor a cero.', 'aviso')
      return
    }
    actualizarMutation.mutate(
      { id: extenderUser.id, data: { dias } },
      {
        onSuccess: () => {
          setExtenderUser(null)
          notificar('Suscripción extendida', `Se agregaron ${dias} días a ${extenderUser.nombre}.`, 'exito')
        },
      },
    )
  }

  const crearUsuario = (e: FormEvent) => {
    e.preventDefault()
    const dias = Number(nuevosDias || '0')
    if (!Number.isInteger(dias) || dias < 0) {
      notificar('Días inválidos', 'Ingresa un número entero mayor o igual a cero.', 'aviso')
      return
    }
    crearMutation.mutate(dias)
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <Shield className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight">Administración de Usuarios</h1>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-16 text-center">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <p className="text-muted-foreground">Error al cargar los usuarios</p>
            <Button onClick={() => refetch()}>Reintentar</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight">Administración de Usuarios</h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Altas, roles, accesos y suscripciones del equipo.
          </p>
        </div>
        <Button className="gap-2" onClick={() => setCrearOpen(true)}>
          <Plus className="h-4 w-4" />
          Nuevo usuario
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard icon={<Users className="h-4 w-4" />} label="Usuarios" value={kpis.total} />
        <KpiCard icon={<UserCheck className="h-4 w-4" />} label="Activos" value={kpis.activos} />
        <KpiCard icon={<Shield className="h-4 w-4" />} label="Administradores" value={kpis.admins} />
        <KpiCard
          icon={<CalendarX className="h-4 w-4" />}
          label="Sin suscripción vigente"
          value={kpis.sinSuscripcion}
        />
      </div>

      <Card>
        <CardHeader className="gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle>Usuarios</CardTitle>
            <span className="text-xs text-muted-foreground">
              {filtrados.length} de {usuarios.length}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-[220px] flex-1 sm:max-w-xs">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                placeholder="Buscar por nombre, correo o rol..."
                className="pl-8"
              />
            </div>
            <select
              className={selectClass}
              value={filtroRol}
              onChange={(e) => setFiltroRol(e.target.value as 'todos' | Rol)}
              aria-label="Filtrar por rol"
            >
              <option value="todos">Todos los roles</option>
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
            <select
              className={selectClass}
              value={filtroEstado}
              onChange={(e) => setFiltroEstado(e.target.value as 'todos' | 'activos' | 'inactivos')}
              aria-label="Filtrar por estado"
            >
              <option value="todos">Todos los estados</option>
              <option value="activos">Activos</option>
              <option value="inactivos">Inactivos</option>
            </select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <TableHead key={header.id} className={header.id === 'acciones' ? 'text-right' : undefined}>
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
                    <TableCell colSpan={columnas.length} className="h-40 text-center text-muted-foreground">
                      <div className="flex items-center justify-center gap-2">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                        Cargando...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : usuarios.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={columnas.length} className="h-40 text-center text-muted-foreground">
                      <div className="flex flex-col items-center gap-2">
                        <Users className="h-8 w-8" />
                        No hay usuarios registrados
                      </div>
                    </TableCell>
                  </TableRow>
                ) : filtrados.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={columnas.length} className="h-40 text-center text-muted-foreground">
                      <div className="flex flex-col items-center gap-2">
                        <Search className="h-8 w-8" />
                        Ningún usuario coincide con los filtros
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <TableRow key={row.id}>
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id} className={cell.column.id === 'acciones' ? 'text-right' : undefined}>
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {!isLoading && filtrados.length > 0 && (
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[rgb(255_255_255_/_0.06)] px-4 py-2.5">
              <span className="text-xs text-muted-foreground">
                Mostrando {table.getRowModel().rows.length} de {filtrados.length}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!table.getCanPreviousPage()}
                  onClick={() => table.previousPage()}
                >
                  Anterior
                </Button>
                <span className="text-xs text-muted-foreground">
                  {table.getPageCount() === 0 ? 0 : table.getState().pagination.pageIndex + 1} / {table.getPageCount()}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!table.getCanNextPage()}
                  onClick={() => table.nextPage()}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Crear usuario */}
      <Dialog open={crearOpen} onOpenChange={setCrearOpen}>
        <DialogContent>
          <form onSubmit={crearUsuario}>
            <DialogHeader>
              <DialogTitle>Nuevo usuario</DialogTitle>
              <DialogDescription>Crea una cuenta y, si quieres, dale días de suscripción.</DialogDescription>
            </DialogHeader>
            <div className="space-y-3 py-4">
              <div className="space-y-1.5">
                <Label htmlFor="nuevo-nombre">Nombre de usuario</Label>
                <Input
                  id="nuevo-nombre"
                  value={nuevoNombre}
                  onChange={(e) => setNuevoNombre(e.target.value)}
                  placeholder="Ej. jperez"
                  minLength={3}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="nuevo-email">Correo</Label>
                <Input
                  id="nuevo-email"
                  type="email"
                  value={nuevoEmail}
                  onChange={(e) => setNuevoEmail(e.target.value)}
                  placeholder="correo@empresa.com"
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="nuevo-password">Contraseña</Label>
                <Input
                  id="nuevo-password"
                  type="password"
                  value={nuevoPassword}
                  onChange={(e) => setNuevoPassword(e.target.value)}
                  placeholder="Mínimo 6 caracteres"
                  minLength={6}
                  required
                />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="nuevo-rol">Rol</Label>
                  <select
                    id="nuevo-rol"
                    className={cn(selectClass, 'w-full')}
                    value={nuevoRol}
                    onChange={(e) => setNuevoRol(e.target.value as Rol)}
                  >
                    {ROLES.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="nuevo-dias">Días de suscripción</Label>
                  <Input
                    id="nuevo-dias"
                    type="number"
                    min={0}
                    max={3650}
                    value={nuevosDias}
                    onChange={(e) => setNuevosDias(e.target.value)}
                  />
                  <p className="text-[11px] text-muted-foreground">0 = sin suscripción (modo gratuito)</p>
                </div>
              </div>
            </div>
            {errorCrear && (
              <p className="mb-3 flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>{errorCrear}</span>
              </p>
            )}
            <DialogFooter>
              <Button variant="outline" type="button" onClick={() => setCrearOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" className="gap-2" disabled={crearMutation.isPending}>
                {crearMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                {crearMutation.isPending ? 'Creando...' : 'Crear usuario'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Restablecer contraseña */}
      <Dialog open={!!passwordUser} onOpenChange={(abierto) => !abierto && setPasswordUser(null)}>
        <DialogContent>
          <form onSubmit={guardarPassword}>
            <DialogHeader>
              <DialogTitle>Restablecer contraseña</DialogTitle>
              <DialogDescription>
                Se asignará una nueva contraseña a {passwordUser?.nombre}. Sus sesiones abiertas se cerrarán
                (salvo la tuya, si estás cambiando la tuya).
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3 py-4">
              <div className="space-y-1.5">
                <Label htmlFor="password-nueva">Nueva contraseña</Label>
                <Input
                  id="password-nueva"
                  type="password"
                  value={passwordNueva}
                  onChange={(e) => setPasswordNueva(e.target.value)}
                  minLength={6}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password-confirmar">Confirmar contraseña</Label>
                <Input
                  id="password-confirmar"
                  type="password"
                  value={passwordConfirmar}
                  onChange={(e) => setPasswordConfirmar(e.target.value)}
                  minLength={6}
                  required
                />
                {errorPassword && <p className="text-xs text-destructive">{errorPassword}</p>}
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" type="button" onClick={() => setPasswordUser(null)}>
                Cancelar
              </Button>
              <Button type="submit" className="gap-2" disabled={actualizarMutation.isPending || !!errorPassword}>
                {actualizarMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <KeyRound className="h-4 w-4" />
                )}
                {actualizarMutation.isPending ? 'Guardando...' : 'Cambiar contraseña'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Extender suscripción */}
      <Dialog open={!!extenderUser} onOpenChange={(abierto) => !abierto && setExtenderUser(null)}>
        <DialogContent>
          <form onSubmit={guardarExtension}>
            <DialogHeader>
              <DialogTitle>Extender suscripción</DialogTitle>
              <DialogDescription>
                {extenderUser?.expira
                  ? `${extenderUser.nombre} tiene suscripción hasta el ${formatFecha(extenderUser.expira)}.`
                  : `${extenderUser?.nombre} no tiene suscripción registrada.`}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-1.5 py-4">
              <Label htmlFor="extender-dias">Días a agregar</Label>
              <Input
                id="extender-dias"
                type="number"
                min={1}
                max={3650}
                value={extenderDias}
                onChange={(e) => setExtenderDias(e.target.value)}
                required
              />
              <p className="text-[11px] text-muted-foreground">
                Si la suscripción ya venció, los días se cuentan desde hoy.
              </p>
            </div>
            <DialogFooter>
              <Button variant="outline" type="button" onClick={() => setExtenderUser(null)}>
                Cancelar
              </Button>
              <Button type="submit" className="gap-2" disabled={actualizarMutation.isPending}>
                {actualizarMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CalendarPlus className="h-4 w-4" />
                )}
                {actualizarMutation.isPending ? 'Guardando...' : 'Extender'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Eliminar usuario */}
      <Dialog open={!!eliminarUser} onOpenChange={(abierto) => !abierto && setEliminarUser(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar usuario</DialogTitle>
            <DialogDescription>
              Se eliminará permanentemente a {eliminarUser?.nombre}
              {eliminarUser?.email ? ` (${eliminarUser.email})` : ''}, junto con sus sesiones y suscripciones.
              Esta acción no se puede deshacer.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEliminarUser(null)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              className="gap-2"
              disabled={eliminarMutation.isPending}
              onClick={() => eliminarUser && eliminarMutation.mutate(eliminarUser.id)}
            >
              {eliminarMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
              {eliminarMutation.isPending ? 'Eliminando...' : 'Eliminar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function KpiCard({ icon, label, value }: { icon: ReactNode; label: string; value: number }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
          {icon}
        </div>
        <div>
          <div className="text-xl font-semibold leading-none">{value}</div>
          <div className="mt-1 text-[11.5px] text-muted-foreground">{label}</div>
        </div>
      </CardContent>
    </Card>
  )
}
