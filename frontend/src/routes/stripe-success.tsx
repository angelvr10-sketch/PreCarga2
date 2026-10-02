import { useEffect, useState } from 'react'
import { useSearch, useNavigate } from '@tanstack/react-router'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { paymentsApi } from '@/lib/payments'
import { CheckCircle, AlertCircle, LayoutDashboard } from 'lucide-react'

type Estado = 'verificando' | 'aprobado' | 'rechazado' | 'error'

export default function StripeSuccess() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const search: Record<string, string> = useSearch({ strict: false })
  const sessionId = search.session_id as string | undefined

  const [estado, setEstado] = useState<Estado>('verificando')

  useEffect(() => {
    if (!sessionId) {
      setEstado('rechazado')
      return
    }

    // El webhook de Stripe es la via principal. Esta llamada es el
    // fallback: si el webhook no llego (se cerraba la pestana, o es
    // desarrollo), el backend procesa el pago aqui.
    paymentsApi
      .success(sessionId)
      .then((res) => {
        setEstado(res.approved ? 'aprobado' : 'rechazado')
        queryClient.invalidateQueries({ queryKey: ['auth', 'me'] })
      })
      .catch(() => setEstado('error'))
  }, [sessionId, queryClient])

  const contenido = {
    verificando: {
      titulo: 'Verificando pago...',
      texto: 'Confirmando tu pago con Stripe.',
      Icono: CheckCircle,
      tono: 'text-muted-foreground bg-muted',
    },
    aprobado: {
      titulo: '¡Pago Exitoso!',
      texto: 'Gracias por tu suscripción. Tu acceso ya está activo.',
      Icono: CheckCircle,
      tono: 'text-emerald-400 bg-emerald-500/10',
    },
    rechazado: {
      titulo: 'Pago no confirmado',
      texto: 'Stripe todavía no confirmó el pago. Si ya te cobraron, contáctanos.',
      Icono: AlertCircle,
      tono: 'text-amber-400 bg-amber-500/10',
    },
    error: {
      titulo: 'Error al verificar',
      texto: 'No pudimos confirmar el pago. Intenta de nuevo en unos minutos.',
      Icono: AlertCircle,
      tono: 'text-destructive bg-destructive/10',
    },
  }[estado]

  const { Icono } = contenido

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Resultado del Pago</h1>

      <div className="mx-auto max-w-md">
        <Card>
          <CardHeader>
            <div className="flex justify-center">
              <div className={`flex h-16 w-16 items-center justify-center rounded-full ${contenido.tono}`}>
                <Icono className={`h-8 w-8 ${estado === 'verificando' ? 'animate-pulse' : ''} ${contenido.tono.split(' ')[0]}`} />
              </div>
            </div>
            <CardTitle className="mt-4 text-center text-2xl">{contenido.titulo}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6 text-center">
            <p className="text-muted-foreground">{contenido.texto}</p>

            {sessionId && (
              <p className="rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
                ID de sesión: {sessionId}
              </p>
            )}

            {estado === 'verificando' ? (
              <div className="flex items-center justify-center gap-2 text-muted-foreground">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                Consultando Stripe
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {estado !== 'aprobado' && (
                  <Button className="w-full gap-2" size="lg" onClick={() => navigate({ to: '/planes' })}>
                    Intentar de nuevo
                  </Button>
                )}
                <Button
                  variant={estado === 'aprobado' ? 'default' : 'outline'}
                  className="w-full gap-2"
                  size="lg"
                  onClick={() => navigate({ to: '/dashboard' })}
                >
                  <LayoutDashboard className="h-4 w-4" />
                  Ir al Dashboard
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
