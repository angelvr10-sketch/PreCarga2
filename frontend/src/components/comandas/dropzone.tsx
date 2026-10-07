/**
 * Zona de arrastre para subir el reporte PDF.
 *
 * Sin dependencias extra: un <input type=file> invisible y un <label> que hace
 * de zona. Funciona igual con clic, con arrastrar y con el teclado (el label
 * es un elemento enfocable), que es lo que hace falta en una PWA que se usa
 * desde el movil.
 *
 * El input se resetea con `e.target.value = ''` despues de subir, para que
 * elegir el MISMO archivo otra vez dispare el evento. Sin eso, subir el mismo
 * reporte dos veces seguidas no hace nada la segunda vez, y es justo el caso
 * de uso de reimportar tras un error.
 */
import { useRef, useState } from 'react'
import { Upload, Loader2, FileUp } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  onSubir: (archivo: File) => void
  subiendo: boolean
  /** Texto del error actual, si lo hay. */
  error?: string | null
  disabled?: boolean
}

const MAX_MB = 20

export function Dropzone({ onSubir, subiendo, error, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [arrastrando, setArrastrando] = useState(false)

  function manejarArchivo(archivo: File | undefined) {
    if (!archivo) return
    onSubir(archivo)
    // Permite volver a elegir el mismo archivo.
    if (inputRef.current) inputRef.current.value = ''
  }

  function alSoltar(e: React.DragEvent) {
    e.preventDefault()
    setArrastrando(false)
    if (subiendo || disabled) return
    manejarArchivo(e.dataTransfer.files?.[0])
  }

  return (
    <div className="space-y-2">
      <div
        onDragOver={(e) => { e.preventDefault(); if (!subiendo && !disabled) setArrastrando(true) }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={alSoltar}
        className={cn(
          'rounded-xl border-2 border-dashed transition-colors',
          arrastrando
            ? 'border-primary bg-primary/5'
            : error
              ? 'border-destructive/40 bg-destructive/5'
              : 'border-primary/30 bg-muted/20 hover:border-primary/60 hover:bg-primary/5',
        )}
      >
        <label
          className={cn(
            'flex cursor-pointer flex-col items-center justify-center gap-2 px-6 py-7 text-center',
            (subiendo || disabled) && 'cursor-not-allowed opacity-60',
          )}
        >
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="sr-only"
            disabled={subiendo || disabled}
            onChange={(e) => manejarArchivo(e.target.files?.[0])}
          />
          {subiendo ? (
            <>
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <span className="text-sm font-medium">Procesando reporte…</span>
              <span className="text-xs text-muted-foreground">
                Se están guardando las comandas
              </span>
            </>
          ) : (
            <>
              <Upload className="h-6 w-6 text-primary" aria-hidden />
              <span className="text-sm font-medium">
                Arrastra el reporte o <span className="text-primary underline">búscalo</span>
              </span>
              <span className="text-xs text-muted-foreground">
                PDF, hasta {MAX_MB} MB. Subirlo dos veces actualiza, no duplica.
              </span>
            </>
          )}
        </label>
      </div>

      {error && (
        <p className="flex items-start gap-1.5 text-xs text-destructive">
          <FileUp className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {error}
        </p>
      )}
    </div>
  )
}
