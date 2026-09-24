import { useNavigate } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { XCircle, CreditCard, LayoutDashboard } from 'lucide-react'

export default function StripeCancel() {
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Resultado del Pago</h1>

      <div className="mx-auto max-w-md">
        <Card>
          <CardHeader>
            <div className="flex justify-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-red-500/10">
                <XCircle className="h-8 w-8 text-red-400" />
              </div>
            </div>
            <CardTitle className="mt-4 text-center text-2xl">Pago Cancelado</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6 text-center">
            <p className="text-muted-foreground">
              El pago fue cancelado. Puedes intentarlo de nuevo cuando quieras.
            </p>

            <div className="flex flex-col gap-3">
              <Button className="w-full gap-2" size="lg" onClick={() => navigate({ to: '/planes' })}>
                <CreditCard className="h-4 w-4" />
                Intentar de nuevo
              </Button>
              <Button variant="outline" className="w-full gap-2" onClick={() => navigate({ to: '/dashboard' })}>
                <LayoutDashboard className="h-4 w-4" />
                Ir al Dashboard
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
