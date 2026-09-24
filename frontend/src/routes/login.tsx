import { useState } from 'react'
import { useNavigate, Link } from '@tanstack/react-router'
import { useForm } from '@tanstack/react-form'
import { useAuth } from '@/hooks/use-auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Ship, Loader2, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [error, setError] = useState<string | null>(null)

  const form = useForm({
    defaultValues: {
      email: '',
      password: '',
    },
    onSubmit: async ({ value }) => {
      setError(null)
      try {
        await login(value.email, value.password)
        navigate({ to: '/dashboard' })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error al iniciar sesión')
      }
    },
  })

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent" />
      <Card className="relative w-full max-w-md">
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Ship className="h-6 w-6 text-primary" />
          </div>
          <CardTitle>Iniciar Sesión</CardTitle>
          <CardDescription>
            Accede a tu cuenta de PreCarga SHAT
          </CardDescription>
        </CardHeader>

        {error && (
          <div className="mx-6 mb-2 flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
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

            <form.Field name="password">
              {(field) => (
                <div className="space-y-2">
                  <Label htmlFor={field.name}>Contraseña</Label>
                  <Input
                    id={field.name}
                    name={field.name}
                    type="password"
                    placeholder="••••••••"
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    autoComplete="current-password"
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
                  {isSubmitting ? 'Iniciando sesión...' : 'Iniciar Sesión'}
                </Button>
              )}
            </form.Subscribe>

            <div className="flex w-full flex-col items-center gap-1 text-sm text-muted-foreground">
              <span>
                ¿No tienes cuenta?{' '}
                <Link to="/registro" className="text-primary underline-offset-4 hover:underline">
                  Registrarse
                </Link>
              </span>
              <Link to="/verificar" className="text-primary underline-offset-4 hover:underline">
                Verificar correo
              </Link>
            </div>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
