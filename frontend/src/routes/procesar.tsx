import { useState, useRef } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useMutation } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { solicitudesApi } from '@/lib/solicitudes'
import { FileText, Upload, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function Procesar() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const mutation = useMutation({
    mutationFn: (f: File) => solicitudesApi.procesarPdf(f),
  })

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = () => {
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile?.type === 'application/pdf') {
      setFile(droppedFile)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected) {
      setFile(selected)
    }
  }

  const handleUpload = () => {
    if (file) {
      mutation.mutate(file)
    }
  }

  const result = mutation.data

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Procesar PDF</h1>

      <Card>
        <CardHeader>
          <CardTitle>Subir archivo PDF</CardTitle>
          <CardDescription>
            Selecciona o arrastra un archivo PDF para procesar los datos de personal
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            className={cn(
              'flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 transition-colors',
              isDragOver
                ? 'border-primary bg-primary/5'
                : 'border-muted-foreground/25 hover:border-muted-foreground/50',
            )}
            onClick={() => inputRef.current?.click()}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <FileText className="mb-4 h-12 w-12 text-muted-foreground" />
            {file ? (
              <p className="text-sm font-medium">{file.name}</p>
            ) : (
              <>
                <p className="mb-1 text-sm font-medium">
                  Arrastra un archivo PDF aquí o haz clic para seleccionar
                </p>
                <p className="text-xs text-muted-foreground">Solo archivos PDF</p>
              </>
            )}
          </div>

          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={handleFileSelect}
          />

          <Button
            className="w-full gap-2"
            disabled={!file || mutation.isPending}
            onClick={handleUpload}
          >
            {mutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            {mutation.isPending ? 'Procesando...' : 'Procesar PDF'}
          </Button>
        </CardContent>
      </Card>

      {mutation.isPending && (
        <Card>
          <CardContent className="flex items-center justify-center gap-3 py-8">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Procesando archivo PDF...</p>
          </CardContent>
        </Card>
      )}

      {mutation.isError && (
        <Card className="border-destructive/50">
          <CardContent className="flex items-center gap-3 py-6">
            <XCircle className="h-6 w-6 shrink-0 text-destructive" />
            <div className="flex-1">
              <p className="font-medium text-destructive">Error</p>
              <p className="text-sm text-muted-foreground">
                {mutation.error instanceof Error ? mutation.error.message : 'Error al procesar el archivo'}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {result && result.ok && (
        <Card className="border-emerald-500/50">
          <CardContent className="space-y-4 py-6">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-6 w-6 shrink-0 text-emerald-400" />
              <div>
                <p className="font-medium text-emerald-400">Procesado exitosamente</p>
                <p className="text-sm text-muted-foreground">{result.mensaje}</p>
              </div>
            </div>
            <Button className="w-full gap-2" onClick={() => navigate({ to: '/altas' })}>
              <FileText className="h-4 w-4" />
              Ver en Altas
            </Button>
          </CardContent>
        </Card>
      )}

      {result && !result.ok && (
        <Card className="border-destructive/50">
          <CardContent className="flex items-center gap-3 py-6">
            <XCircle className="h-6 w-6 shrink-0 text-destructive" />
            <div>
              <p className="font-medium text-destructive">Error</p>
              <p className="text-sm text-muted-foreground">{result.mensaje}</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
