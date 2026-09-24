import { createContext, useContext, type ReactNode } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { authApi } from '@/lib/auth'
import type { Usuario } from '@/types'

interface AuthContextType {
  user: Usuario | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (nombre: string, email: string, password: string) => Promise<void>
  verify: (email: string, codigo: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()

  const { data: user, isLoading } = useQuery({
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

  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      queryClient.setQueryData(['auth', 'me'], null)
      queryClient.clear()
    },
  })

  return (
    <AuthContext.Provider
      value={{
        user: user ?? null,
        isLoading,
        isAuthenticated: !!user,
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
          await logoutMutation.mutateAsync()
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}
