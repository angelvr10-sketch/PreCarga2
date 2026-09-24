import { Maximize2, Minimize2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface FullscreenToggleProps {
  isFullscreen: boolean
  onToggle: () => void
}

export function FullscreenToggle({ isFullscreen, onToggle }: FullscreenToggleProps) {
  return (
    <Button
      variant="ghost"
      size="icon-sm"
      onClick={onToggle}
      title={isFullscreen ? 'Salir de pantalla completa' : 'Ver en pantalla completa'}
      aria-label={isFullscreen ? 'Salir de pantalla completa' : 'Ver en pantalla completa'}
    >
      {isFullscreen ? <Minimize2 /> : <Maximize2 />}
    </Button>
  )
}