import { useState, type FormEvent } from 'react'
import { Link } from '@tanstack/react-router'
import { useMutation } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { BrandMark } from '@/components/brand'
import { authApi } from '@/lib/auth'
import { AlertCircle, CheckCircle2, KeyRound, Loader2, Mail } from 'lucide-react'

type Paso = 'solicitar' | 'restablecer' | 'listo'

function mensajeError(error: unknown): string {
  return error instanceof Error ? error.message : 'Ocurrió un error. Intenta de nuevo.'
}

export default function Recuperar() {
  const [paso, setPaso] = useState<Paso>('solicitar')
  const [email, setEmail] = useState('')
  const [codigo, setCodigo] = useState('')
  const [nueva, setNueva] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [aviso, setAviso] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const solicitar = useMutation({
    mutationFn: (correo: string) => authApi.forgotPassword(correo),
    onSuccess: (res) => {
      setError(null)
      setAviso(res.mensaje || 'Si el correo está registrado, enviamos un código.')
      setPaso('restablecer')
    },
    onError: (err) => {
      setAviso(null)
      setError(mensajeError(err))
    },
  })

  const restablecer = useMutation({
    mutationFn: () => authApi.resetPassword(email, codigo, nueva),
    onSuccess: (res) => {
      setError(null)
      setAviso(res.mensaje || 'Contraseña actualizada. Ya puedes iniciar sesión.')
      setPaso('listo')
    },
    onError: (err) => setError(mensajeError(err)),
  })

  const enviarSolicitud = (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    solicitar.mutate(email.trim())
  }

  const enviarCambio = (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (nueva.length < 6) {
      setError('La nueva contraseña debe tener al menos 6 caracteres')
      return
    }
    if (nueva !== confirmar) {
      setError('Las contraseñas no coinciden')
      return
    }
    restablecer.mutate()
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent" />
      <Card className="relative w-full max-w-md">
        <CardHeader className="items-center text-center">
          <BrandMark alt="" className="mb-2 h-9" />
          <CardTitle>
            {paso === 'solicitar' && 'Recuperar contraseña'}
            {paso === 'restablecer' && 'Revisa tu correo'}
            {paso === 'listo' && 'Contraseña actualizada'}
          </CardTitle>
          <CardDescription>
            {paso === 'solicitar' &&
              'Escribe el correo de tu cuenta y te enviaremos un código de 6 dígitos.'}
            {paso === 'restablecer' &&
              'Ingresa el código que enviamos a tu correo y elige una nueva contraseña.'}
            {paso === 'listo' && 'Ya puedes entrar con tu nueva contraseña.'}
          </CardDescription>
        </CardHeader>

        {error && (
          <div className="mx-6 mb-2 flex items-start gap-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {aviso && paso !== 'listo' && (
          <div className="mx-6 mb-2 flex items-start gap-2 rounded-md bg-primary/10 px-3 py-2 text-sm text-primary">
            <Mail className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{aviso}</span>
          </div>
        )}

        {paso === 'solicitar' && (
          <form onSubmit={enviarSolicitud}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Correo electrónico</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="correo@ejemplo.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoFocus
                  required
                />
              </div>
            </CardContent>
            <CardFooter className="flex flex-col gap-3">
              <Button type="submit" className="w-full gap-2" disabled={solicitar.isPending}>
                {solicitar.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Mail className="h-4 w-4" />
                )}
                {solicitar.isPending ? 'Enviando...' : 'Enviar código'}
              </Button>
              <Link to="/login" className="text-sm text-primary underline-offset-4 hover:underline">
                Volver a iniciar sesión
              </Link>
            </CardFooter>
          </form>
        )}

        {paso === 'restablecer' && (
          <form onSubmit={enviarCambio}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="codigo">Código de 6 dígitos</Label>
                <Input
                  id="codigo"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="000000"
                  maxLength={6}
                  value={codigo}
                  onChange={(e) => setCodigo(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  autoFocus
                  required
                />
                <p className="text-xs text-muted-foreground">
                  Enviado a <span className="text-foreground">{email}</span>. Revisa también el spam.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="nueva">Nueva contraseña</Label>
                <Input
                  id="nueva"
                  type="password"
                  autoComplete="new-password"
                  value={nueva}
                  onChange={(e) => setNueva(e.target.value)}
                  minLength={6}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirmar">Confirmar nueva contraseña</Label>
                <Input
                  id="confirmar"
                  type="password"
                  autoComplete="new-password"
                  value={confirmar}
                  onChange={(e) => setConfirmar(e.target.value)}
                  minLength={6}
                  required
                />
              </div>
            </CardContent>
            <CardFooter className="flex flex-col gap-3">
              <Button type="submit" className="w-full gap-2" disabled={restablecer.isPending || codigo.length !== 6}>
                {restablecer.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <KeyRound className="h-4 w-4" />
                )}
                {restablecer.isPending ? 'Guardando...' : 'Restablecer contraseña'}
              </Button>
              <div className="flex w-full flex-col items-center gap-1 text-sm text-muted-foreground">
                <button
                  type="button"
                  className="text-primary underline-offset-4 hover:underline disabled:opacity-50"
                  disabled={solicitar.isPending}
                  onClick={() => {
                    setError(null)
                    solicitar.mutate(email)
                  }}
                >
                  Reenviar código
                </button>
                <button
                  type="button"
                  className="text-primary underline-offset-4 hover:underline"
                  onClick={() => {
                    setError(null)
                    setAviso(null)
                    setCodigo('')
                    setNueva('')
                    setConfirmar('')
                    setPaso('solicitar')
                  }}
                >
                  Usar otro correo
                </button>
              </div>
            </CardFooter>
          </form>
        )}

        {paso === 'listo' && (
          <CardContent className="flex flex-col items-center gap-4 py-6 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <CheckCircle2 className="h-6 w-6 text-primary" />
            </div>
            <p className="text-sm text-muted-foreground">{aviso}</p>
            <Link to="/login" className="text-sm text-primary underline-offset-4 hover:underline">
              Iniciar sesión
            </Link>
          </CardContent>
        )}
      </Card>
    </div>
  )
}
