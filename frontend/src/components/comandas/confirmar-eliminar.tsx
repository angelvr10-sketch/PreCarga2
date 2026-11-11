/**
 * Confirmación de borrado de UNA comanda.
 *
 * No se borra al clic en el tacho: la tabla abre el detalle al hacer clic en
 * cualquier parte de la fila, así que un borrado directo sería demasiado fácil
 * de disparar sin querer. El diálogo dice exactamente qué se va a borrar
 * (folio, compañía, destino, PAX y fecha) para que la persona lo reconozca.
 */
import { Loader2, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { fechaCorta } from '@/lib/comandas'
import type { Comanda } from '@/types/comandas'

interface Props {
  /** La comanda a borrar, o null para cerrar el diálogo. */
  comanda: Comanda | null
  fecha: string
  borrando: boolean
  onCerrar: () => void
  onConfirmar: () => Promise<void>
}

export function ConfirmarEliminarComanda({
  comanda,
  fecha,
  borrando,
  onCerrar,
  onConfirmar,
}: Props) {
  return (
    <Dialog
      open={!!comanda}
      onOpenChange={(v) => {
        if (!v && !borrando) onCerrar()
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Trash2 className="h-4 w-4 text-destructive" />
            Eliminar comanda
          </DialogTitle>
          <DialogDescription>
            Se borra esta comanda del {fechaCorta(fecha)}. Las demás del día no se
            tocan. Para recuperarla hay que capturarla otra vez a mano.
          </DialogDescription>
        </DialogHeader>

        {comanda && (
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 rounded-md border border-border/60 bg-muted/40 p-3 text-sm">
            <dt className="text-muted-foreground">Folio</dt>
            <dd className="font-mono font-semibold">{comanda.comanda}</dd>

            <dt className="text-muted-foreground">Compañía</dt>
            <dd className="truncate" title={comanda.compania}>{comanda.compania}</dd>

            <dt className="text-muted-foreground">Destino</dt>
            <dd className="truncate" title={comanda.destino}>{comanda.destino}</dd>

            <dt className="text-muted-foreground">PAX</dt>
            <dd className="tabular-nums">{comanda.pax}</dd>

            <dt className="text-muted-foreground">Tipo</dt>
            <dd>{comanda.tipo === 'MORTERA' ? 'Mortera' : 'Vianda'}</dd>
          </dl>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onCerrar} disabled={borrando}>
            Cancelar
          </Button>
          <Button
            variant="destructive"
            className="gap-2"
            disabled={borrando}
            onClick={() => void onConfirmar()}
          >
            {borrando ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
            {borrando ? 'Eliminando…' : 'Eliminar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
