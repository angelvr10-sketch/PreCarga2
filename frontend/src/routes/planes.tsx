import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { paymentsApi } from '@/lib/payments'
import { CreditCard, Download } from 'lucide-react'

interface Plan {
  id: string
  nombre: string
  precio: number
  descargas: number
}

export default function Planes() {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['planes'],
    queryFn: () => paymentsApi.listPlans(),
  })

  const planes = (data as Plan[]) ?? []

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Planes de Suscripción</h1>
        <div className="grid gap-6 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <div className="h-6 w-24 animate-pulse rounded bg-muted" />
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="h-10 w-28 animate-pulse rounded bg-muted" />
                <div className="h-4 w-36 animate-pulse rounded bg-muted" />
                <div className="h-10 w-full animate-pulse rounded bg-muted" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (planes.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold tracking-tight">Planes de Suscripción</h1>
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-16 text-muted-foreground">
            <CreditCard className="h-8 w-8" />
            No hay planes disponibles
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Planes de Suscripción</h1>

      <div className="grid gap-6 md:grid-cols-3">
        {planes.map((plan) => (
          <Card key={plan.id} className="flex flex-col">
            <CardHeader>
              <CardTitle className="text-xl">{plan.nombre}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-1 flex-col justify-between space-y-6">
              <div className="space-y-2">
                <p className="text-3xl font-bold">
                  ${plan.precio.toLocaleString()} MXN
                </p>
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Download className="h-4 w-4" />
                  {plan.descargas} descargas incluidas
                </p>
              </div>
              <Button
                className="w-full gap-2"
                onClick={() =>
                  navigate({ to: '/checkout', search: { plan_id: plan.id } })
                }
              >
                <CreditCard className="h-4 w-4" />
                Seleccionar
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
