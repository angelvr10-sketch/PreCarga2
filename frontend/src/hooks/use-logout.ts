import { useCallback } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useAuth } from '@/hooks/use-auth'

/**
 * Logout + navegacion al landing en un solo paso.
 *
 * Vive aqui y no dentro de AuthProvider porque el provider se monta POR
 * ENCIMA de <RouterProvider> (main.tsx), donde useNavigate() todavia no
 * existe. Asi cualquier boton de "Cerrar Sesion" queda obligado a
 * redirigir; el guard de rutas protegidas no ayuda, porque beforeLoad
 * solo corre en transiciones y no se re-evalua al perder la sesion.
 *
 * replace: true evita que el boton "atras" devuelva al usuario al
 * dashboard, que el guard rebotaria a /login y pareceria un bug.
 */
export function useLogout() {
  const { logout } = useAuth()
  const navigate = useNavigate()

  return useCallback(async () => {
    await logout()
    await navigate({ to: '/', replace: true })
  }, [logout, navigate])
}
