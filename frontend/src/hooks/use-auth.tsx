import { createContext, useCallback, useContext, useEffect, useMemo, useRef, type ReactNode } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { authApi } from '@/lib/auth'
import type { Usuario } from '@/types'

interface AuthContextType {
  user: Usuario | null
  isLoading: boolean
  isAuthenticated: boolean
  /** Resuelve cuando la consulta inicial de /api/auth/me ya termino. */
  whenReady: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  register: (nombre: string, email: string, password: string) => Promise<void>
  verify: (email: string, codigo: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()

  const { data: user, isLoading, isFetched } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      try {
        const res = await authApi.me()
        return res.user
      } catch {
        return null
      }
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  // El guard del router necesita ESPERAR a que auth resuelva, no permitir
  // el paso mientras carga. Se resuelve una sola vez por carga de pagina.
  // OJO: resolveReadyRef debe declararse ANTES de usarse dentro del
  // executor; al revés cae en zona muerta temporal (ReferenceError).
  const resolveReadyRef = useRef<(() => void) | null>(null)
  const readyRef = useRef<Promise<void> | null>(null)
  if (readyRef.current === null) {
    readyRef.current = new Promise<void>((resolve) => {
      resolveReadyRef.current = resolve
    })
  }

  useEffect(() => {
    if (isFetched) resolveReadyRef.current?.()
  }, [isFetched])

  const whenReady = useCallback(() => readyRef.current ?? Promise.resolve(), [])

  const loginMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.login(email, password),
    onSuccess: (data) => {
      if (data.user) {
        queryClient.setQueryData(['auth', 'me'], data.user)
      }
    },
  })

  const registerMutation = useMutation({
    mutationFn: ({ nombre, email, password }: { nombre: string; email: string; password: string }) =>
      authApi.register(nombre, email, password),
  })

  const verifyMutation = useMutation({
    mutationFn: ({ email, codigo }: { email: string; codigo: string }) =>
      authApi.verify(email, codigo),
    onSuccess: (data) => {
      if (data.user) {
        queryClient.setQueryData(['auth', 'me'], data.user)
      }
    },
  })

  // Descarta la sesion local. NO se usa queryClient.clear(): destruye la
  // query activa ['auth','me'] y su observer vuelve a pedir /api/auth/me,
  // lo que reintroduce un fetch (y un 401) en pleno logout. Ademas el
  // clear() de antes se comia el setQueryData inmediatamente anterior.
  const clearSession = useCallback(() => {
    queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== 'auth' })
    queryClient.setQueryData(['auth', 'me'], null)
  }, [queryClient])

  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSuccess: clearSession,
  })

  // Sin useMemo, este objeto y sus 5 funciones nuevas en cada render
  // re-renderizan todo el arbol del router que cuelga debajo.
  const value = useMemo<AuthContextType>(
    () => ({
      user: user ?? null,
      isLoading,
      isAuthenticated: !!user,
      whenReady,
        login: async (email, password) => {
          const result = await loginMutation.mutateAsync({ email, password })
          if (!result.ok) throw new Error(result.mensaje || 'Error al iniciar sesión')
        },
        register: async (nombre, email, password) => {
          const result = await registerMutation.mutateAsync({ nombre, email, password })
          if (!result.ok) throw new Error(result.mensaje || 'Error al registrarse')
        },
        verify: async (email, codigo) => {
          const result = await verifyMutation.mutateAsync({ email, codigo })
          if (!result.ok) throw new Error(result.mensaje || 'Código inválido')
        },
        logout: async () => {
          // Si el POST falla (red caida, 500) la sesion local se descarta
          // igual: dejar al usuario atrapado en una ruta protegida es peor
          // que una cookie huerfana, que sola expira en 24h.
          try {
            await logoutMutation.mutateAsync()
          } catch {
            clearSession()
          }
        },
    }),
    [user, isLoading, whenReady, loginMutation, registerMutation, verifyMutation, logoutMutation, clearSession],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}
