import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { router } from '@/router'
import { solicitudesApi } from '@/lib/solicitudes'
import { activosApi } from '@/lib/activos'
import { Search, FileText, Package } from 'lucide-react'
import { cn } from '@/lib/utils'

type Item =
  | { kind: 'solicitud'; id: number; folio: string; sub: string }
  | { kind: 'activo'; nombre: string }

export function SearchPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<Item[]>([])
  const [active, setActive] = useState(0)
  const [cargando, setCargando] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const activosQ = useQuery({
    queryKey: ['activos'],
    queryFn: () => activosApi.list(),
    // Se necesita para filtrar por nombre en el buscador global
  })

  // Reset al abrir: la ultima busqueda no debe quedarse rondando
  useEffect(() => {
    if (open) {
      setQ('')
      setResults([])
      setActive(0)
    }
  }, [open])

  // Debounce + buscar en solicitudes (API) y activos (local)
  useEffect(() => {
    const t = q.trim()
    if (!t) {
      setResults([])
      return
    }
    setCargando(true)
    const timer = setTimeout(async () => {
      try {
        const r = await solicitudesApi.list(1, t)
        const sols: Item[] = (r.solicitudes ?? []).map((s) => ({
          kind: 'solicitud',
          id: s.id,
          folio: s.folio,
          sub: [s.compania, s.destino].filter(Boolean).join(' · '),
        }))
        const act = (activosQ.data ?? [])
          .filter((a) => a.nombre.toLowerCase().includes(t.toLowerCase()))
          .slice(0, 5)
          .map((a): Item => ({ kind: 'activo', nombre: a.nombre }))
        setResults([...sols, ...act].slice(0, 12))
        setActive(0)
      } catch {
        setResults([])
      } finally {
        setCargando(false)
      }
    }, 250)
    return () => {
      clearTimeout(timer)
      setCargando(false)
    }
  }, [q, activosQ.data])

  const ir = (item: Item | undefined) => {
    if (!item) return
    onOpenChange(false)
    if (item.kind === 'solicitud') {
      // /altas lee ?search= una vez al montar y si ya esta montado se sincroniza
      // via el listener de abajo
      router.history.push(`/altas?search=${encodeURIComponent(q.trim())}`)
    } else {
      router.history.push(`/activos?search=${encodeURIComponent(q.trim())}`)
    }
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((a) => Math.min(a + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => Math.max(a - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      ir(results[active])
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl gap-0 p-0">
        <DialogTitle className="sr-only">Buscar solicitudes y activos</DialogTitle>
        <div className="border-b border-white/10 p-3">
          <Input
            ref={inputRef}
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Buscar solicitudes, activos…"
            className="h-9"
          />
        </div>
        <div className="max-h-96 overflow-y-auto p-2">
          {cargando && <p className="px-3 py-2 text-xs text-muted-foreground">Buscando…</p>}
          {!cargando && q.trim() !== '' && results.length === 0 && (
            <p className="px-3 py-2 text-xs text-muted-foreground">Sin resultados</p>
          )}
          {!cargando && results.length > 0 && (
            <ul className="space-y-0.5">
              {results.map((item, i) => (
                <li key={item.kind === 'solicitud' ? `s${item.id}` : `a${item.nombre}`}>
                  <button
                    type="button"
                    onMouseEnter={() => setActive(i)}
                    onClick={() => ir(item)}
                    className={cn(
                      'flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-left transition-colors',
                      i === active ? 'bg-white/10' : 'hover:bg-white/5',
                    )}
                  >
                    {item.kind === 'solicitud' ? (
                      <FileText className="h-4 w-4 shrink-0 text-blue-400" />
                    ) : (
                      <Package className="h-4 w-4 shrink-0 text-teal-400" />
                    )}
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium">
                        {item.kind === 'solicitud' ? item.folio : item.nombre}
                      </span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {item.kind === 'solicitud' ? item.sub : 'Activo'}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <p className="px-3 pb-1 pt-2 text-[11px] text-muted-foreground/70">
            ↑ ↓ para navegar · Enter para abrir · Esc para cerrar
          </p>
        </div>
      </DialogContent>
    </Dialog>
  )
}
