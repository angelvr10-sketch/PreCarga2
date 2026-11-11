/**
 * Formulario de una comanda, para CREAR y para MODIFICAR.
 *
 * Es el mismo diálogo en los dos casos. Al modificar se bloquea el folio y no se
 * pide la fecha: los dos son la llave de la fila (folio, subido_por,
 * fecha_registro) y el backend rechaza un cuerpo que intente moverlos.
 *
 * La validación de aquí es mínima a propósito —required y números—: las reglas
 * de verdad (folio sin espacios, horario HH:MM, transporte de la lista, PAX
 * entero) viven UNA sola vez, en `core/comandas/edicion.py`, y el 400 vuelve con
 * el motivo escrito y se muestra en el toast. Duplicarlas en el navegador sería
 * dos sitios que se desincronizan.
 *
 * PAX no se edita: es la suma de MENU 1 + MENU 2 (`Comanda.total_pax`). Aquí se
 * calcula para mostrarlo y el backend lo vuelve a derivar, de modo que la API
 * tampoco pueda guardar un total incoherente con los menús.
 */
import { useEffect, useState } from 'react'
import { ChevronDown, Loader2, Plus, Save } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { Comanda, ComandaEntrada, TipoComanda } from '@/types/comandas'

/** La misma lista cerrada que `parser.TRANSPORTES` y `edicion.TRANSPORTES`. */
const TRANSPORTES = ['AEREO', 'GANGWAY', 'MARÍTIMO', 'VIUDA', 'CANASTILLA']

interface Props {
  abierto: boolean
  /** null = crear. Una comanda = modificar esa. */
  comanda: Comanda | null
  /** Fecha de la comanda al modificar; la seleccionada al crear. */
  fecha: string
  /** Hay una petición en vuelo: el formulario no se puede cerrar. */
  guardando: boolean
  onCerrar: () => void
  /** Resuelve true si se guardó. El que llama cierra el diálogo. */
  onGuardar: (entrada: ComandaEntrada) => Promise<boolean>
}

interface Formulario {
  fecha: string
  comanda: string
  horario: string
  compania: string
  destino: string
  menu_1: string
  menu_2: string
  transporte: string
  tipo: TipoComanda
  observaciones: string
}

const VACIO: Formulario = {
  fecha: '',
  comanda: '',
  horario: '',
  compania: '',
  destino: '',
  menu_1: '',
  menu_2: '',
  transporte: '',
  tipo: 'VIANDA',
  observaciones: '',
}

function desdeComanda(c: Comanda, fecha: string): Formulario {
  return {
    fecha,
    comanda: c.comanda,
    horario: c.horario,
    compania: c.compania,
    destino: c.destino,
    menu_1: String(c.menu_1),
    menu_2: String(c.menu_2),
    transporte: c.transporte,
    tipo: c.tipo,
    observaciones: c.observaciones,
  }
}

/** Número de un <input>, tolerando vacío (que el backend lee como 0). */
function numero(valor: string): number {
  const limpio = valor.trim()
  if (limpio === '') return 0
  const n = Number(limpio)
  return Number.isFinite(n) ? n : 0
}

export function FormularioComanda({
  abierto,
  comanda,
  fecha,
  guardando,
  onCerrar,
  onGuardar,
}: Props) {
  const esEdicion = !!comanda
  const [form, setForm] = useState<Formulario>(VACIO)
  // PAX es derivado: no se edita, siempre es Menú 1 + Menú 2.
  const paxCalculado = numero(form.menu_1) + numero(form.menu_2)

  // Cada vez que se abre, el formulario se reinicia: al crear queda vacío y al
  // modificar trae lo que hay en la base. Sin esto se verían los datos de la
  // comanda anterior.
  useEffect(() => {
    if (!abierto) return
    setForm(comanda ? desdeComanda(comanda, fecha) : { ...VACIO, fecha })
  }, [abierto, comanda, fecha])

  const campo =
    (nombre: keyof Formulario) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [nombre]: e.target.value }))

  async function enviar(e: React.FormEvent) {
    e.preventDefault()

    const entrada: ComandaEntrada = {
      horario: form.horario,
      compania: form.compania.trim(),
      destino: form.destino.trim(),
      pax: paxCalculado,
      transporte: form.transporte,
      menu_1: numero(form.menu_1),
      menu_2: numero(form.menu_2),
      tipo: form.tipo,
      observaciones: form.observaciones.trim(),
    }

    if (!esEdicion) {
      // La fecha y el folio solo viajan al crear: al modificar son la llave y
      // van en la URL.
      entrada.fecha = form.fecha
      entrada.comanda = form.comanda.trim()
    }

    await onGuardar(entrada)
    // El cierre lo decide `onGuardar`: si falló, el diálogo sigue abierto con
    // lo que la persona ya había escrito.
  }

  return (
    <Dialog
      open={abierto}
      onOpenChange={(v) => {
        if (!v && !guardando) onCerrar()
      }}
    >
      <DialogContent className="max-h-[92vh] overflow-y-auto">
        <form onSubmit={enviar} className="space-y-4">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {esEdicion ? (
                <Save className="h-4 w-4 text-primary" />
              ) : (
                <Plus className="h-4 w-4 text-primary" />
              )}
              {esEdicion ? (
                <span className="font-mono">{comanda?.comanda}</span>
              ) : (
                'Nueva comanda'
              )}
            </DialogTitle>
            <DialogDescription>
              {esEdicion
                ? 'Corrige los datos de la comanda. El folio no se puede cambiar: para eso hay que borrarla y crearla de nuevo.'
                : 'Para lo que no viene en el reporte PDF. Se guarda en la fecha indicada.'}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-3 sm:grid-cols-2">
            {esEdicion ? (
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="cmd-folio">Folio</Label>
                <Input id="cmd-folio" value={form.comanda} readOnly disabled
                       className="font-mono" />
              </div>
            ) : (
              <>
                <div className="space-y-1.5">
                  <Label htmlFor="cmd-fecha">Fecha</Label>
                  <Input id="cmd-fecha" type="date" value={form.fecha}
                         onChange={campo('fecha')} required />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="cmd-folio">Folio</Label>
                  <Input id="cmd-folio" value={form.comanda} onChange={campo('comanda')}
                         placeholder="OCT001" autoFocus required />
                </div>
              </>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="cmd-horario">Horario</Label>
              <Input id="cmd-horario" type="time" value={form.horario}
                     onChange={campo('horario')} required />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="cmd-pax">PAX</Label>
              <Input id="cmd-pax" type="number" value={paxCalculado}
                     readOnly tabIndex={-1} aria-readonly="true"
                     className="cursor-default bg-[rgb(255_255_255_/_0.02)] tabular-nums text-muted-foreground" />
              <p className="text-[11px] text-muted-foreground">
                Se calcula: Menú 1 + Menú 2.
              </p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="cmd-compania">Compañía</Label>
              <Input id="cmd-compania" value={form.compania}
                     onChange={campo('compania')} placeholder="NORCONTROL" required />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="cmd-destino">Destino</Label>
              <Input id="cmd-destino" value={form.destino}
                     onChange={campo('destino')} placeholder="ABKATUN A" required />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="cmd-transporte">Transporte</Label>
              <div className="relative">
                <select
                  id="cmd-transporte"
                  value={form.transporte}
                  onChange={campo('transporte')}
                  className="h-8 w-full appearance-none rounded-md border border-[rgb(255_255_255_/_0.10)] bg-[rgb(255_255_255_/_0.04)] px-3 pr-9 text-[13.5px] focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                >
                  <option value="">Sin especificar</option>
                  {TRANSPORTES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="cmd-tipo">Tipo</Label>
              <div className="relative">
                <select
                  id="cmd-tipo"
                  value={form.tipo}
                  onChange={campo('tipo')}
                  className="h-8 w-full appearance-none rounded-md border border-[rgb(255_255_255_/_0.10)] bg-[rgb(255_255_255_/_0.04)] px-3 pr-9 text-[13.5px] focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                >
                  <option value="VIANDA">Vianda</option>
                  <option value="MORTERA">Mortera</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="cmd-menu1">Menú 1</Label>
              <Input id="cmd-menu1" type="number" min={0} inputMode="numeric"
                     value={form.menu_1} onChange={campo('menu_1')} />
              <p className="text-[11px] text-muted-foreground">
                Comidas del menú 1.
              </p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="cmd-menu2">Menú 2</Label>
              <Input id="cmd-menu2" type="number" min={0} inputMode="numeric"
                     value={form.menu_2} onChange={campo('menu_2')} />
              <p className="text-[11px] text-muted-foreground">Comidas extra; se suman al PAX.</p>
            </div>

            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="cmd-obs">Observaciones</Label>
              <textarea
                id="cmd-obs"
                value={form.observaciones}
                onChange={campo('observaciones')}
                rows={2}
                maxLength={500}
                placeholder="Custodio, indicaciones, referencias…"
                className="w-full rounded-md border border-[rgb(255_255_255_/_0.10)] bg-[rgb(255_255_255_/_0.04)] px-3 py-2 text-[13.5px] placeholder:text-muted-foreground/70 focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onCerrar} disabled={guardando}>
              Cancelar
            </Button>
            <Button type="submit" className="gap-2" disabled={guardando}>
              {guardando ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : esEdicion ? (
                <Save className="h-4 w-4" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              {guardando ? 'Guardando…' : esEdicion ? 'Guardar cambios' : 'Crear comanda'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
