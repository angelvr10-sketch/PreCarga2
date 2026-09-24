import { useState } from 'react'
import { useNavigate, Link } from '@tanstack/react-router'
import { useForm } from '@tanstack/react-form'
import { useAuth } from '@/hooks/use-auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Mail, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react'

export default function Verificar() {
  const navigate = useNavigate()
  const emailFromParams = new URLSearchParams(window.location.search).get('email')
  const { verify } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [resendMessage, setResendMessage] = useState(false)

  const form = useForm({
    defaultValues: {
      email: emailFromParams || '',
      codigo: '',
    },
    onSubmit: async ({ value }) => {
      setError(null)
      if (!value.email) {
        setError('El correo electrónico es requerido')
        return
      }
      try {
        await verify(value.email, value.codigo)
        navigate({ to: '/dashboard' })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Código inválido')
      }
    },
  })

  const handleResend = () => {
    setResendMessage(true)
    setTimeout(() => setResendMessage(false), 3000)
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent" />
      <Card className="relative w-full max-w-md">
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Mail className="h-6 w-6 text-primary" />
          </div>
          <CardTitle>Verificar Correo</CardTitle>
          <CardDescription>
            Ingresa el código de verificación de 6 dígitos que enviamos a tu correo
          </CardDescription>
        </CardHeader>

        {error && (
          <div className="mx-6 mb-2 flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {resendMessage && (
          <div className="mx-6 mb-2 flex items-center gap-2 rounded-md bg-emerald-500/10 px-3 py-2 text-sm text-emerald-400">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>Código reenviado exitosamente</span>
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault()
            e.stopPropagation()
            form.handleSubmit()
          }}
        >
          <CardContent className="space-y-4">
            <form.Field name="email">
              {(field) => (
                <div className="space-y-2">
                  <Label htmlFor={field.name}>Correo electrónico</Label>
                  <Input
                    id={field.name}
                    name={field.name}
                    type="text"
                    placeholder="correo@ejemplo.com"
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    autoComplete="email"
                  />
                </div>
              )}
            </form.Field>

            <form.Field name="codigo">
              {(field) => (
                <div className="space-y-2">
                  <Label htmlFor={field.name}>Código de verificación</Label>
                  <Input
                    id={field.name}
                    name={field.name}
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    placeholder="000000"
                    className="text-center text-lg tracking-[0.5em]"
                    value={field.state.value}
                    onChange={(e) => {
                      const val = e.target.value.replace(/\D/g, '').slice(0, 6)
                      field.handleChange(val)
                    }}
                    autoComplete="one-time-code"
                  />
                </div>
              )}
            </form.Field>
          </CardContent>

          <CardFooter className="flex flex-col gap-3">
            <form.Subscribe selector={(state) => state.isSubmitting}>
              {(isSubmitting) => (
                <Button
                  type="submit"
                  className="w-full"
                  disabled={isSubmitting}
                >
                  {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {isSubmitting ? 'Verificando...' : 'Verificar Código'}
                </Button>
              )}
            </form.Subscribe>

            <div className="flex w-full flex-col items-center gap-1 text-sm text-muted-foreground">
              <button
                type="button"
                onClick={handleResend}
                className="text-primary underline-offset-4 hover:underline"
              >
                Reenviar código
              </button>
              <Link to="/login" className="text-primary underline-offset-4 hover:underline">
                Volver a inicio de sesión
              </Link>
            </div>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
