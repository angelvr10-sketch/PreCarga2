import { useCallback, useEffect, useRef, useState } from 'react'

export function useFullscreen<T extends HTMLElement>() {
  const ref = useRef<T | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [native, setNative] = useState(false)

  useEffect(() => {
    const onChange = () => {
      setNative(Boolean(document.fullscreenElement))
      setIsFullscreen(Boolean(document.fullscreenElement))
    }
    document.addEventListener('fullscreenchange', onChange)
    return () => document.removeEventListener('fullscreenchange', onChange)
  }, [])

  const toggle = useCallback(() => {
    const el = ref.current
    if (!el) return
    if (isFullscreen) {
      if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => {})
      }
      setIsFullscreen(false)
      return
    }
    if (el.requestFullscreen) {
      el.requestFullscreen()
        .then(() => {
          setNative(true)
          setIsFullscreen(true)
        })
        .catch(() => setIsFullscreen(true))
    } else {
      setIsFullscreen(true)
    }
  }, [isFullscreen])

  return { ref, isFullscreen, native, toggle }
}