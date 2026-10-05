import { useEffect, useState } from 'react'
import { useLocation } from '@tanstack/react-router'
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { VERSION, CAMBIOS } from '@/lib/changelog'

const CLAVE = 'changelog_visto'

function yaVisto(): boolean {
  return localStorage.getItem(CLAVE) === VERSION
}

export function ChangelogModal() {
  const [open, setOpen] = useState(false)
  const location = useLocation()

  // Se muestra solo una vez por version, y solo en el Dashboard (igual que
  // precarga). localStorage evita el efecto visual de reabrir al cerrar.
  useEffect(() => {
    if (location.pathname === '/dashboard' && !yaVisto()) setOpen(true)
  }, [location.pathname])

  // Leyendo el evento que dispara el item "Novedades" del sidebar.
  // SiEl trigger manual no debe depender de localStorage: el usuario querra
  // volver a verlo cuantas veces quiera.
  useEffect(() => {
    const abrir = () => setOpen(true)
    window.addEventListener('precarga:open-changelog', abrir)
    return () => window.removeEventListener('precarga:open-changelog', abrir)
  }, [])

  const marcarVisto = () => {
    localStorage.setItem(CLAVE, VERSION)
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o)
        // Marcar como visto solo cuando el usuario lo cierra: asi se vuelve a
        // mostrar hasta que el usuario realmente lo cierre una vez esta version.
        if (!o) marcarVisto()
      }}
    >
      <DialogContent className="max-w-2xl overflow-hidden">
        <DialogTitle className="flex items-center gap-2 text-lg">
          <span>🚀</span> Últimas actualizaciones
        </DialogTitle>
        <DialogDescription className="text-xs">v{VERSION}</DialogDescription>
        <ul className="max-h-[60vh] space-y-3 overflow-y-auto fluent-scroll pr-1">
          {CAMBIOS.map((c) => (
            <li key={c.titulo} className="flex gap-3 text-sm">
              <span aria-hidden className="mt-0.5 shrink-0">{c.icono}</span>
              <span>
                <strong className="text-foreground">{c.titulo}:</strong>{' '}
                <span className="text-muted-foreground">{c.detalle}</span>
              </span>
            </li>
          ))}
        </ul>
        <div className="flex justify-end pt-2">
          <button
            type="button"
            onClick={() => {
              setOpen(false)
              marcarVisto()
            }}
            className="rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-white/10 hover:text-foreground"
          >
            Entendido
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
