import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { adminApi } from '@/lib/admin'
import { Download, FileText, AlertCircle, X } from 'lucide-react'
import { descargarLog, mensajeDescargaError } from '@/lib/solicitudes'

export default function Logs() {
  const [aviso, setAviso] = useState<string | null>(null)

  // window.open('/api/descargar-log', '_blank') dejaba una pestana vacia y
  // navegaba la actual si la descarga fallaba. Con fetch no hay pestana.
  const bajarLog = async () => {
    const r = await descargarLog()
    if (!r.ok) setAviso(mensajeDescargaError(r.motivo))
  }

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['logs'],
    queryFn: () => adminApi.getLogs(),
  })

  if (isError) {
    return (
      <div className="space-y-6">
        {aviso && (
          <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span className="flex-1">{aviso}</span>
            <button type="button" onClick={() => setAviso(null)}
                    className="shrink-0 opacity-70 hover:opacity-100" aria-label="Cerrar aviso">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold tracking-tight">Logs del Sistema</h1>
          <Button onClick={() => void bajarLog()}>
            <Download className="mr-2 h-4 w-4" />
            Descargar Log
          </Button>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-16 text-center">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <p className="text-muted-foreground">Error al cargar los logs</p>
            <Button onClick={() => refetch()}>Reintentar</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {aviso && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span className="flex-1">{aviso}</span>
          <button type="button" onClick={() => setAviso(null)}
                  className="shrink-0 opacity-70 hover:opacity-100" aria-label="Cerrar aviso">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Logs del Sistema</h1>
        <Button onClick={() => void bajarLog()}>
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
