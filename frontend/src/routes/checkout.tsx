import { useQuery, useMutation } from '@tanstack/react-query'
import { useSearch, useNavigate } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { paymentsApi } from '@/lib/payments'
import { CreditCard, Loader2, Download, AlertCircle, ArrowLeft } from 'lucide-react'

interface Plan {
  id: string
  nombre: string
  precio: number
  descargas: number
}

export default function Checkout() {
  const navigate = useNavigate()
  const search: Record<string, string> = useSearch({ strict: false })
  const planId = search.plan_id as string
  const noDownloads = search.no_downloads === '1'

  const { data, isLoading } = useQuery({
    queryKey: ['planes'],
    queryFn: () => paymentsApi.listPlans(),
  })

  const plan = ((data as Plan[]) ?? []).find((p: Plan) => p.id === planId)

  const mutation = useMutation({
    mutationFn: (id: string) => paymentsApi.createCheckout(id),
    onSuccess: (data) => {
      window.location.href = data.url
    },
  })

  if (!planId) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Checkout</h1>
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-16 text-muted-foreground">
            <AlertCircle className="h-8 w-8" />
            <p className="text-lg font-medium">No se especificó un plan</p>
            <Button variant="outline" className="mt-4 gap-2" onClick={() => navigate({ to: '/planes' })}>
              <ArrowLeft className="h-4 w-4" />
              Ver Planes
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (noDownloads) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Checkout</h1>
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-16 text-muted-foreground">
            <AlertCircle className="h-8 w-8 text-yellow-400" />
            <p className="text-lg font-medium">Has alcanzado el límite de descargas gratuitas</p>
            <p className="text-sm">Adquiere un plan para seguir descargando</p>
            <Button variant="outline" className="mt-4 gap-2" onClick={() => navigate({ to: '/planes' })}>
              <ArrowLeft className="h-4 w-4" />
              Ver Planes
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Checkout</h1>

      {isLoading && (
        <Card>
          <CardContent className="py-12">
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Cargando información del plan...</p>
            </div>
          </CardContent>
        </Card>
      )}

      {!isLoading && !plan && (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-16 text-muted-foreground">
            <AlertCircle className="h-8 w-8" />
            <p className="text-lg font-medium">Plan no encontrado</p>
            <Button variant="outline" className="mt-4 gap-2" onClick={() => navigate({ to: '/planes' })}>
              <ArrowLeft className="h-4 w-4" />
              Ver Planes
            </Button>
          </CardContent>
        </Card>
      )}

      {!isLoading && plan && (
        <div className="mx-auto max-w-md">
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">{plan.nombre}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <p className="text-4xl font-bold">${plan.precio.toLocaleString()} MXN</p>
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Download className="h-4 w-4" />
                  {plan.descargas} descargas incluidas
                </p>
              </div>

              <Badge variant="secondary" className="w-full justify-center py-2 text-sm">
                Pago único por suscripción
              </Badge>

              <Button
                className="w-full gap-2"
                size="lg"
                disabled={mutation.isPending}
                onClick={() => mutation.mutate(planId)}
              >
                {mutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Redirigiendo a Stripe...
                  </>
                ) : (
                  <>
                    <CreditCard className="h-4 w-4" />
                    Ir a Pagar
                  </>
                )}
              </Button>

              {mutation.isError && (
                <p className="flex items-center gap-2 text-sm text-destructive">
                  <AlertCircle className="h-4 w-4" />
                  Error al procesar el pago. Intenta de nuevo.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
