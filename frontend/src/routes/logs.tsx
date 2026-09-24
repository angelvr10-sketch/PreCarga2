import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { adminApi } from '@/lib/admin'
import { Download, FileText } from 'lucide-react'

export default function Logs() {
  const { data, isLoading } = useQuery({
    queryKey: ['logs'],
    queryFn: () => adminApi.getLogs(),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Logs del Sistema</h1>
        <Button onClick={() => window.open('/api/descargar-log', '_blank')}>
          <Download className="mr-2 h-4 w-4" />
          Descargar Log
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            {data?.fecha ? (
              <>Registro del {data.fecha}</>
            ) : (
              'Registro del Sistema'
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              Cargando logs...
            </div>
          ) : !data ? (
            <div className="flex flex-col items-center gap-2 py-16 text-muted-foreground">
              <FileText className="h-8 w-8" />
              No hay logs disponibles
            </div>
          ) : (
            <pre className="max-h-[600px] overflow-auto rounded-lg bg-muted p-4 font-mono text-sm leading-relaxed">
              <code>{data.contenido}</code>
            </pre>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
