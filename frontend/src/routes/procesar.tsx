import { useRef, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { solicitudesApi, descargarSolicitud, mensajeDescargaError } from '@/lib/solicitudes'
import { FileText, CheckCircle2, XCircle, Loader2, X, FileWarning } from 'lucide-react'
import { cn } from '@/lib/utils'

type Estado = 'pendiente' | 'procesando' | 'ok' | 'error'

type Item = {
  id: number
  file: File
  estado: Estado
  mensaje?: string
}

const esPdf = (f: File) => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')

export default function Procesar() {
  const navigate = useNavigate()
  const [items, setItems] = useState<Item[]>([])
  const [procesando, setProcesando] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)
  const [ignorados, setIgnorados] = useState<string[]>([])
  const inputRef = useRef<HTMLInputElement>(null)
  const nextId = useRef(1)
  // Cola de archivos por procesar y bandera del bucle en marcha.
  //
  // Se procesa en serie porque el parseo de PDF es CPU-bound y el backend
  // abre peticiones a Supabase por cada persona: lanzarlos en paralelo solo
  // competingiria por la CPU y por el pool de conexiones.
  //
  // La cola tambien resuelve el autoarranque: si el usuario suelta mas
  // archivos mientras corre el proceso, se encolan y los toma el mismo bucle.
  // Sin esto, cada archivo nuevo abriria su propio bucle y el "uno por uno"
  // dejaria de ser cierto justo cuando hay mas carga.
  const colaRef = useRef<Item[]>([])
  const corriendoRef = useRef(false)
  // Cambia la key del input para poder volver a elegir el mismo archivo.
  const [resetKey, setResetKey] = useState(0)

  const anadir = (files: FileList | File[]) => {
    const lista = Array.from(files)
    if (lista.length === 0) return

    const pdfs = lista.filter(esPdf)
    const otros = lista.filter((f) => !esPdf(f))
    // Los no-PDF se avisan en vez de descartarse en silencio: si se cuela un
    // .xlsx al arrastrar, hay que decirlo.
    setIgnorados(otros.map((f) => f.name))

    // Se calcula la lista de nuevos aqui y no dentro del updater de
    // setItems: hace falta encolar esos mismos archivos para el autoarranque,
    // y un updater de React corre dos veces en StrictMode.
    const yaPresentes = new Set(items.map((i) => `${i.file.name}-${i.file.size}`))
    const nuevos: Item[] = []
    for (const f of pdfs) {
      const clave = `${f.name}-${f.size}`
      if (yaPresentes.has(clave)) continue // no duplicar el mismo archivo
      yaPresentes.add(clave)
      nuevos.push({ id: nextId.current++, file: f, estado: 'pendiente' })
    }

    if (nuevos.length === 0) return
    setItems((prev) => [...prev, ...nuevos])
    // Autoarranque: en vez de esperar al boton, encola y arranca el bucle.
    encolar(nuevos)
  }

  const quitar = (id: number) => setItems((prev) => prev.filter((i) => i.id !== id))

  const limpiar = () => {
    setItems([])
    setIgnorados([])
    colaRef.current = []
    setResetKey((k) => k + 1)
  }

  /** Mete archivos en la cola y arranca el bucle si no habia ninguno. */
  const encolar = (nuevos: Item[]) => {
    colaRef.current = [...colaRef.current, ...nuevos]
    void vaciarCola()
  }

  /**
   * Bucle unico que consume la cola de a uno.
   *
   * Devuelve de inmediato si ya hay otro bucle corriendo: los archivos que
   * se solen durante el proceso quedan en la cola y los toma esta misma
   * vuelta, en vez de abrir una descarga paralela.
   */
  const vaciarCola = async () => {
    if (corriendoRef.current) return
    corriendoRef.current = true
    setProcesando(true)

    try {
      while (colaRef.current.length > 0) {
        const item = colaRef.current.shift()!
        const actualizar = (parche: Partial<Item>) =>
          setItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, ...parche } : i)))

        actualizar({ estado: 'procesando' })
        try {
          const r = await solicitudesApi.procesarPdf(item.file)
          // Ojo: un fallo del backend llega como HTTP 200 con {ok:false}; no es
          // una excepcion, asi que hay que mirar el campo ok.
          if (!r.ok) {
            actualizar({ estado: 'error', mensaje: r.mensaje })
            continue
          }

          // Descarga automatica del xlsx recien generado.
          if (r.archivo) {
            try {
              const d = await descargarSolicitud(r.archivo)
              if (d.ok) {
                actualizar({ estado: 'ok', mensaje: `${r.mensaje} · descargado` })
              } else {
                // El PDF SI se proceso y guardo bien: solo fallo la descarga, asi
                // que el estado sigue siendo 'ok' con el aviso.
                actualizar({
                  estado: 'ok',
                  mensaje: `${r.mensaje} · sin descargar: ${mensajeDescargaError(d.motivo).toLowerCase()}`,
                })
              }
            } catch (e) {
              const motivo = e instanceof Error ? e.message : 'Error al descargar'
              actualizar({ estado: 'ok', mensaje: `${r.mensaje} · sin descargar: ${motivo}` })
            }
          } else {
            actualizar({ estado: 'ok', mensaje: r.mensaje })
          }
        } catch (e) {
          actualizar({
            estado: 'error',
            mensaje: e instanceof Error ? e.message : 'Error al procesar el archivo',
          })
        }
      }
    } finally {
      corriendoRef.current = false
      setProcesando(false)
    }
  }

  const pendientes = items.filter((i) => i.estado === 'pendiente').length
  const ok = items.filter((i) => i.estado === 'ok').length
  const conError = items.filter((i) => i.estado === 'error').length
  const terminado = !procesando && items.length > 0 && pendientes === 0
  const enCurso = items.find((i) => i.estado === 'procesando')

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Procesar PDF</h1>

      <Card>
        <CardHeader>
          <CardTitle>Subir archivos PDF</CardTitle>
          <CardDescription>
            El procesamiento arranca solo al elegir o soltar los archivos
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault()
              setIsDragOver(true)
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setIsDragOver(false)
              // dataTransfer.files es una FileList con VARIOS archivos: hay que
              // recorrerla entera, no quedarse con files[0].
              anadir(e.dataTransfer.files)
            }}
            className={cn(
              'flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 transition-colors',
              isDragOver
                ? 'border-primary bg-primary/5'
                : 'border-muted-foreground/25 hover:border-muted-foreground/50',
            )}
          >
            <FileText className="mb-4 h-12 w-12 text-muted-foreground" />
            <p className="mb-1 text-sm font-medium">
              Arrastra uno o varios archivos PDF aquí o haz clic para seleccionar
            </p>
            <p className="text-xs text-muted-foreground">
              Solo archivos PDF · se procesan automáticamente
            </p>
          </div>

          {ignorados.length > 0 && (
            <div className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-200">
              <FileWarning className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                Se ignoraron {ignorados.length === 1 ? 'el archivo' : 'los archivos'} que no
                son PDF: {ignorados.join(', ')}
              </span>
            </div>
          )}

          {/* El atributo `multiple` es el arreglo del bug: sin el, el selector del
              sistema deja elegir UN unico archivo y al arrastrar varios solo se
              detectaba el primero. */}
          <input
            key={resetKey}
            ref={inputRef}
            type="file"
            accept=".pdf,application/pdf"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files) anadir(e.target.files)
              // Permite volver a seleccionar el mismo archivo despues.
              e.target.value = ''
            }}
          />

          {items.length > 0 && (
            <ul className="space-y-2">
              {items.map((i) => (
                <li
                  key={i.id}
                  className={cn(
                    'flex items-start gap-3 rounded-md border border-white/10 bg-black/30 p-3',
                    i.estado === 'ok' && 'border-emerald-500/40',
                    i.estado === 'error' && 'border-destructive/50',
                  )}
                >
                  <span className="mt-0.5 shrink-0">
                    {i.estado === 'procesando' ? (
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    ) : i.estado === 'ok' ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    ) : i.estado === 'error' ? (
                      <XCircle className="h-4 w-4 text-destructive" />
                    ) : (
                      <FileText className="h-4 w-4 text-muted-foreground" />
                    )}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{i.file.name}</p>
                    {i.mensaje && (
                      <p
                        className={cn(
                          'text-xs',
                          i.estado === 'error' ? 'text-destructive' : 'text-muted-foreground',
                        )}
                      >
                        {i.mensaje}
                      </p>
                    )}
                  </div>
                  {!procesando && (
                    <button
                      type="button"
                      onClick={() => quitar(i.id)}
                      aria-label={`Quitar ${i.file.name}`}
                      className="shrink-0 rounded p-1 text-muted-foreground transition-colors hover:bg-white/10 hover:text-foreground"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}

          {/* Ya no hay boton de "Procesar": al soltar o elegir los archivos
              arrancan solos. Queda solo Limpiar, y durante el proceso se
              muestra el avance en su lugar para no dejar un boton muerto. */}
          {items.length > 0 && !procesando && (
            <div className="flex justify-end">
              <Button variant="outline" size="sm" onClick={limpiar}>
                Limpiar lista
              </Button>
            </div>
          )}

          {procesando && enCurso && (
            <p className="text-center text-xs text-muted-foreground">
              Procesando {enCurso.file.name}… ({ok} de {items.length} listos)
            </p>
          )}
        </CardContent>
      </Card>

      {terminado && (
        <Card className={conError === 0 ? 'border-emerald-500/50' : 'border-amber-500/50'}>
          <CardContent className="space-y-4 py-6">
            <div className="flex items-center gap-3">
              {conError === 0 ? (
                <CheckCircle2 className="h-6 w-6 shrink-0 text-emerald-400" />
              ) : (
                <XCircle className="h-6 w-6 shrink-0 text-amber-400" />
              )}
              <div>
                <p
                  className={cn('font-medium', conError === 0 ? 'text-emerald-400' : 'text-amber-400')}
                >
                  {ok} de {items.length} {items.length === 1 ? 'archivo' : 'archivos'}
                  {conError > 0 && ` · ${conError} con error`}
                </p>
                <p className="text-sm text-muted-foreground">
                  {conError === 0
                    ? 'Procesados exitosamente'
                    : 'Revisa en la lista los archivos con error'}
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              {ok > 0 && (
                <Button className="flex-1 gap-2" onClick={() => navigate({ to: '/altas' })}>
                  <FileText className="h-4 w-4" />
                  Ver en Altas
                </Button>
              )}
              <Button variant="outline" onClick={limpiar}>
                Procesar otros
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
