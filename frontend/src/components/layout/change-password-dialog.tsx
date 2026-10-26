import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
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
import { authApi } from '@/lib/auth'
import { notificar } from '@/hooks/use-toast'
import { AlertCircle, KeyRound, Loader2 } from 'lucide-react'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ChangePasswordDialog({ open, onOpenChange }: Props) {
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [confirmar, setConfirmar] = useState('')

  const mutation = useMutation({
    mutationFn: () => authApi.changePassword(actual, nueva),
    onSuccess: () => {
      notificar(
        'Contraseña actualizada',
        'Se cerraron tus demás sesiones. Esta sigue abierta.',
        'exito',
      )
      cerrar(false)
    },
  })

  function cerrar(abierto: boolean) {
    if (!abierto) {
      setActual('')
      setNueva('')
      setConfirmar('')
      mutation.reset()
    }
    onOpenChange(abierto)
  }

  const error = mutation.error instanceof Error ? mutation.error.message : null
  const noCoinciden = confirmar.length > 0 && nueva !== confirmar

  const enviar = (e: FormEvent) => {
    e.preventDefault()
    if (nueva.length < 6) {
      notificar('Contraseña demasiado corta', 'Usa al menos 6 caracteres.', 'aviso')
      return
    }
    if (nueva !== confirmar) return
    mutation.mutate()
  }

  return (
    <Dialog open={open} onOpenChange={cerrar}>
      <DialogContent>
        <form onSubmit={enviar}>
          <DialogHeader>
            <DialogTitle>Cambiar contraseña</DialogTitle>
            <DialogDescription>
              Ingresa tu contraseña actual y la nueva. Al guardar se cerrarán tus
              otras sesiones abiertas.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-4">
            <div className="space-y-1.5">
              <Label htmlFor="password-actual">Contraseña actual</Label>
              <Input
                id="password-actual"
                type="password"
                autoComplete="current-password"
                value={actual}
                onChange={(e) => setActual(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password-nueva-propia">Nueva contraseña</Label>
              <Input
                id="password-nueva-propia"
                type="password"
                autoComplete="new-password"
                value={nueva}
                onChange={(e) => setNueva(e.target.value)}
                minLength={6}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password-confirmar-propia">Confirmar nueva contraseña</Label>
              <Input
                id="password-confirmar-propia"
                type="password"
                autoComplete="new-password"
                value={confirmar}
                onChange={(e) => setConfirmar(e.target.value)}
                minLength={6}
                required
              />
              {noCoinciden && <p className="text-xs text-destructive">Las contraseñas no coinciden</p>}
            </div>
          </div>

          {error && (
            <p className="mb-3 flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>{error}</span>
            </p>
          )}

          <DialogFooter>
            <Button variant="outline" type="button" onClick={() => cerrar(false)}>
              Cancelar
            </Button>
            <Button
              type="submit"
              className="gap-2"
              disabled={mutation.isPending || noCoinciden || !actual || nueva.length < 6}
            >
              {mutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <KeyRound className="h-4 w-4" />
              )}
              {mutation.isPending ? 'Guardando...' : 'Cambiar contraseña'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
