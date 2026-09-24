import { useEffect } from 'react'
import { useSearch, useNavigate } from '@tanstack/react-router'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CheckCircle, LayoutDashboard } from 'lucide-react'

export default function StripeSuccess() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const search: Record<string, string> = useSearch({ strict: false })
  const sessionId = search.session_id as string

  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: ['auth', 'me'] })
  }, [queryClient])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Resultado del Pago</h1>

      <div className="mx-auto max-w-md">
        <Card>
          <CardHeader>
            <div className="flex justify-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/10">
                <CheckCircle className="h-8 w-8 text-emerald-400" />
              </div>
            </div>
            <CardTitle className="mt-4 text-center text-2xl">¡Pago Exitoso!</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6 text-center">
            <p className="text-muted-foreground">
              Gracias por tu suscripción
            </p>

            {sessionId && (
              <p className="rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
                ID de sesión: {sessionId}
              </p>
            )}

            <Button className="w-full gap-2" size="lg" onClick={() => navigate({ to: '/dashboard' })}>
              <LayoutDashboard className="h-4 w-4" />
              Ir al Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
