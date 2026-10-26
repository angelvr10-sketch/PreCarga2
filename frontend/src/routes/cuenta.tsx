import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ChangePasswordDialog } from '@/components/layout/change-password-dialog'
import { useAuth } from '@/hooks/use-auth'
import { notificar } from '@/hooks/use-toast'
import { authApi } from '@/lib/auth'
import { paymentsApi, type Pago } from '@/lib/payments'
import { formatFecha } from '@/lib/utils'
import {
  AlertCircle,
  BadgeCheck,
  CalendarDays,
  CreditCard,
  Download,
  KeyRound,
  Loader2,
  Mail,
  ReceiptText,
  ShieldCheck,
  UserRound,
} from 'lucide-react'

function mensajeError(error: unknown): string {
  return error instanceof Error ? error.message : 'Intenta de nuevo'
}

function dinero(valor: number | null | undefined): string {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
  }).format(Number(valor) || 0)
}

function EstadoPago({ estado }: { estado: string }) {
  const valor = (estado || '').toLowerCase()
  if (valor === 'approved') return <Badge variant="success">Aprobado</Badge>
  if (valor === 'pending') return <Badge variant="warning">Pendiente</Badge>
  if (valor === 'failed' || valor === 'rejected') {
    return <Badge variant="destructive">Fallido</Badge>
  }
  return <Badge variant="subtle">{estado || '—'}</Badge>
}

function ResumenCard({ children }: { children: ReactNode }) {
  return <Card><CardContent className="space-y-3 p-5">{children}</CardContent></Card>
}

export default function Cuenta() {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const [nombre, setNombre] = useState('')
  const [email, setEmail] = useState('')
  const [actual, setActual] = useState('')
  const [passwordOpen, setPasswordOpen] = useState(false)

  useEffect(() => {
    if (!user) return
    setNombre(user.nombre)
    setEmail(user.email)
  }, [user?.nombre, user?.email])

  const historial = useQuery({
    queryKey: ['pagos', 'historial'],
    queryFn: () => paymentsApi.history(),
  })

  const pagos = (historial.data?.pagos ?? []) as Pago[]

  const perfil = useMutation({
    mutationFn: (datos: { nombre: string; email: string; actual?: string }) =>
      authApi.updateProfile(datos),
    onSuccess: (res) => {
      if (res.user) queryClient.setQueryData(['auth', 'me'], res.user)
      setActual('')
      notificar('Datos actualizados', 'Tu información de cuenta se guardó correctamente.', 'exito')
    },
    onError: (error) => {
      notificar('No se pudieron guardar los datos', mensajeError(error), 'error')
    },
  })

  if (!user) return null

  const emailNormalizado = email.trim().toLowerCase()
  const cambioEmail = emailNormalizado !== (user.email || '').trim().toLowerCase()
  const hayCambios = nombre.trim() !== user.nombre || cambioEmail

  const enviar = (e: FormEvent) => {
    e.preventDefault()
    if (!hayCambios) return
    if (nombre.trim().length < 3) {
      notificar('Nombre demasiado corto', 'Usa al menos 3 caracteres.', 'aviso')
      return
    }
    if (cambioEmail && !actual) {
      notificar(
        'Contraseña requerida',
        'Para cambiar tu correo escribe tu contraseña actual.',
        'aviso',
      )
      return
    }
    perfil.mutate({
      nombre: nombre.trim(),
      email: emailNormalizado,
      ...(cambioEmail ? { actual } : {}),
    })
  }

  const totalGratis = user.descargas_gratis_total ?? 30
  const restantes = user.descargas_gratis_restantes
    ?? Math.max(0, totalGratis - (user.descargas_usadas ?? 0))
  const usadas = user.descargas_usadas ?? Math.max(0, totalGratis - restantes)
  const porcentajeUsado = totalGratis > 0
    ? Math.min(100, Math.round((usadas / totalGratis) * 100))
    : 0
  const vigente = user.suscripcion_vigente ?? false
  const dias = user.dias_restantes ?? 0

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2">
          <UserRound className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight">Mi cuenta</h1>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Administra tus datos, revisa tu suscripción y consulta tus compras.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Datos personales</CardTitle>
            <CardDescription>
              Tu nombre de usuario también sirve para iniciar sesión.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={enviar} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="cuenta-nombre">Nombre de usuario</Label>
                <div className="relative">
                  <UserRound className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="cuenta-nombre"
                    value={nombre}
                    onChange={(e) => setNombre(e.target.value)}
                    className="pl-9"
                    minLength={3}
                    maxLength={120}
                    required
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Label htmlFor="cuenta-email">Correo electrónico</Label>
                  {user.verificado ? (
                    <Badge variant="success" className="gap-1">
                      <BadgeCheck className="h-3 w-3" />
                      Verificado
                    </Badge>
                  ) : (
                    <Badge variant="warning">Sin verificar</Badge>
                  )}
                </div>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="cuenta-email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-9"
                    required
                  />
                </div>
              </div>

              {cambioEmail && (
                <div className="space-y-1.5 rounded-md border border-amber-500/30 bg-amber-500/10 p-3">
                  <Label htmlFor="cuenta-actual">Contraseña actual</Label>
                  <Input
                    id="cuenta-actual"
                    type="password"
                    autoComplete="current-password"
                    value={actual}
                    onChange={(e) => setActual(e.target.value)}
                    placeholder="Necesaria para cambiar el correo"
                  />
                  <p className="text-xs text-muted-foreground">
                    El correo nuevo quedará marcado como “sin verificar”.
                  </p>
                </div>
              )}

              <div className="flex flex-wrap items-center gap-2 pt-1">
                <Button type="submit" disabled={!hayCambios || perfil.isPending}>
                  {perfil.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                  {perfil.isPending ? 'Guardando...' : 'Guardar cambios'}
                </Button>
                {hayCambios && (
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={perfil.isPending}
                    onClick={() => {
                      setNombre(user.nombre)
                      setEmail(user.email)
                      setActual('')
                    }}
                  >
                    Descartar
                  </Button>
                )}
              </div>
            </form>

            <Separator className="my-5" />

            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium">Contraseña</p>
                <p className="text-xs text-muted-foreground">
                  Cambia tu contraseña y cierra las demás sesiones abiertas.
                </p>
              </div>
              <Button variant="outline" className="gap-2" onClick={() => setPasswordOpen(true)}>
                <KeyRound className="h-4 w-4" />
                Cambiar contraseña
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6 lg:col-span-2">
          <ResumenCard>
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-sm font-medium">
                <ShieldCheck className="h-4 w-4 text-primary" />
                Suscripción
              </div>
              {vigente ? (
                <Badge variant="success">Activa</Badge>
              ) : user.expira ? (
                <Badge variant="destructive">Vencida</Badge>
              ) : (
                <Badge variant="subtle">Sin suscripción</Badge>
              )}
            </div>

            <div className="flex items-end justify-between gap-3">
              <div>
                <div className="text-2xl font-semibold leading-none">
                  {vigente ? `${dias} día${dias === 1 ? '' : 's'}` : '—'}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {vigente
                    ? `Restantes · vence el ${formatFecha(user.expira)}`
                    : user.expira
                      ? `Venció el ${formatFecha(user.expira)}`
                      : 'No has comprado un plan'}
                </p>
              </div>
              <CalendarDays className="h-5 w-5 text-muted-foreground" />
            </div>

            <Button asChild variant="outline" size="sm" className="w-full gap-2">
              <Link to="/planes">
                <CreditCard className="h-4 w-4" />
                Ver planes
              </Link>
            </Button>
          </ResumenCard>

          <ResumenCard>
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Download className="h-4 w-4 text-primary" />
                Descargas gratis
              </div>
              <span className="text-xs text-muted-foreground">
                {usadas} de {totalGratis} usadas
              </span>
            </div>

            <div className="flex items-end gap-2">
              <span className="text-3xl font-semibold leading-none">{restantes}</span>
              <span className="pb-0.5 text-xs text-muted-foreground">
                disponible{restantes === 1 ? '' : 's'}
              </span>
            </div>

            <div className="h-2 w-full overflow-hidden rounded-full bg-[rgb(255_255_255_/_0.08)]">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${porcentajeUsado}%` }}
              />
            </div>

            <p className="text-xs text-muted-foreground">
              {vigente
                ? 'Con tu suscripción activa las descargas son ilimitadas.'
                : restantes > 0
                  ? `Te quedan ${restantes} descarga${restantes === 1 ? '' : 's'} gratuita${restantes === 1 ? '' : 's'}.`
                  : 'Te quedaste sin descargas gratis. Compra un plan para seguir descargando.'}
            </p>
          </ResumenCard>
        </div>
      </div>

      <Card>
        <CardHeader className="gap-1">
          <CardTitle className="flex items-center gap-2">
            <ReceiptText className="h-5 w-5 text-primary" />
            Historial de compras
          </CardTitle>
          <CardDescription>Tus pagos más recientes en la aplicación.</CardDescription>
        </CardHeader>
        <CardContent>
          {historial.isLoading ? (
            <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando compras...
            </div>
          ) : historial.isError ? (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <AlertCircle className="h-7 w-7 text-destructive" />
              <p className="text-sm text-muted-foreground">No se pudo cargar el historial.</p>
              <Button size="sm" variant="outline" onClick={() => void historial.refetch()}>
                Reintentar
              </Button>
            </div>
          ) : pagos.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <CreditCard className="h-7 w-7 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Aún no tienes compras</p>
                <p className="text-xs text-muted-foreground">
                  Cuando contrates un plan aparecerá aquí.
                </p>
              </div>
              <Button asChild size="sm" className="gap-2">
                <Link to="/planes">
                  <CreditCard className="h-4 w-4" />
                  Ver planes
                </Link>
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Concepto</TableHead>
                  <TableHead>Monto</TableHead>
                  <TableHead className="text-right">Estado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pagos.map((pago) => (
                  <TableRow key={pago.id}>
                    <TableCell className="whitespace-nowrap text-muted-foreground">
                      {formatFecha(pago.creado) || '—'}
                    </TableCell>
                    <TableCell>
                      Suscripción
                      {pago.dias_comprados
                        ? ` · ${pago.dias_comprados} día${pago.dias_comprados === 1 ? '' : 's'}`
                        : ''}
                    </TableCell>
                    <TableCell className="whitespace-nowrap font-medium">
                      {dinero(pago.monto)}
                    </TableCell>
                    <TableCell className="text-right">
                      <EstadoPago estado={pago.estado} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <ChangePasswordDialog open={passwordOpen} onOpenChange={setPasswordOpen} />
    </div>
  )
}
