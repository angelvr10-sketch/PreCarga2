import { useState } from 'react'
import { useNavigate, Link } from '@tanstack/react-router'
import { useForm } from '@tanstack/react-form'
import { useAuth } from '@/hooks/use-auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Ship, Loader2, AlertCircle } from 'lucide-react'

interface FormValues {
  nombre: string
  email: string
  password: string
  confirmPassword: string
}

function validateEmail(email: string): string | undefined {
  if (!email) return 'El correo es requerido'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Correo electrónico inválido'
  return undefined
}

function validatePassword(password: string): string | undefined {
  if (!password) return 'La contraseña es requerida'
  if (password.length < 6) return 'La contraseña debe tener al menos 6 caracteres'
  return undefined
}

function validateConfirmPassword(confirmPassword: string, password: string): string | undefined {
  if (!confirmPassword) return 'Confirma tu contraseña'
  if (confirmPassword !== password) return 'Las contraseñas no coinciden'
  return undefined
}

export default function Registro() {
  const navigate = useNavigate()
  const { register } = useAuth()
  const [error, setError] = useState<string | null>(null)

  const form = useForm({
    defaultValues: {
      nombre: '',
      email: '',
      password: '',
      confirmPassword: '',
    } satisfies FormValues,
    onSubmit: async ({ value }) => {
      setError(null)
      const passwordErr = validatePassword(value.password)
      if (passwordErr) {
        setError(passwordErr)
        return
      }
      const confirmErr = validateConfirmPassword(value.confirmPassword, value.password)
      if (confirmErr) {
        setError(confirmErr)
        return
      }
      try {
        await register(value.nombre, value.email, value.password)
        navigate({ to: '/verificar', search: { email: value.email } })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error al registrarse')
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
          <CardTitle>Crear Cuenta</CardTitle>
          <CardDescription>
            Regístrate para usar PreCarga SHAT
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
            <form.Field name="nombre">
              {(field) => (
                <div className="space-y-2">
                  <Label htmlFor={field.name}>Nombre completo</Label>
                  <Input
                    id={field.name}
                    name={field.name}
                    placeholder="Juan Pérez"
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    autoComplete="name"
                  />
                </div>
              )}
            </form.Field>

            <form.Field
              name="email"
              validators={{ onChange: ({ value }) => validateEmail(value) }}
            >
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
                  {field.state.meta.errors.length > 0 && (
                    <p className="text-sm text-destructive">{field.state.meta.errors[0]}</p>
                  )}
                </div>
              )}
            </form.Field>

            <form.Field
              name="password"
              validators={{ onChange: ({ value }) => validatePassword(value) }}
            >
              {(field) => (
                <div className="space-y-2">
                  <Label htmlFor={field.name}>Contraseña</Label>
                  <Input
                    id={field.name}
                    name={field.name}
                    type="password"
                    placeholder="Mínimo 6 caracteres"
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    autoComplete="new-password"
                  />
                  {field.state.meta.errors.length > 0 && (
                    <p className="text-sm text-destructive">{field.state.meta.errors[0]}</p>
                  )}
                </div>
              )}
            </form.Field>

            <form.Field
              name="confirmPassword"
              validators={{
                onChange: ({ value, fieldApi }) => {
                  const password = fieldApi.form.getFieldValue('password')
                  return validateConfirmPassword(value, password)
                },
              }}
            >
              {(field) => (
                <div className="space-y-2">
                  <Label htmlFor={field.name}>Confirmar contraseña</Label>
                  <Input
                    id={field.name}
                    name={field.name}
                    type="password"
                    placeholder="Repite la contraseña"
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    autoComplete="new-password"
                  />
                  {field.state.meta.errors.length > 0 && (
                    <p className="text-sm text-destructive">{field.state.meta.errors[0]}</p>
                  )}
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
                  {isSubmitting ? 'Creando cuenta...' : 'Crear Cuenta'}
                </Button>
              )}
            </form.Subscribe>

            <p className="text-sm text-muted-foreground">
              ¿Ya tienes cuenta?{' '}
              <Link to="/login" className="text-primary underline-offset-4 hover:underline">
                Iniciar Sesión
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
