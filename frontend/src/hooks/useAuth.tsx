import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { toast } from 'sonner'

import { SESSION_EXPIRED_EVENT, tokenStore } from '../api/client'
import { authApi } from '../api/endpoints'
import type { TokenResponse, User } from '../types/api'

interface AuthState {
  user: User | null
  status: 'loading' | 'authenticated' | 'anonymous'
  login: (email: string, password: string) => Promise<User>
  register: (fullName: string, email: string, password: string) => Promise<User>
  logout: () => Promise<void>
  setUser: (user: User) => void
  acceptToken: (response: TokenResponse) => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<AuthState['status']>(() => (tokenStore.get() ? 'loading' : 'anonymous'))

  useEffect(() => {
    if (!tokenStore.get()) return
    authApi
      .me()
      .then((u) => {
        setUser(u)
        setStatus('authenticated')
      })
      .catch(() => {
        tokenStore.clear()
        setStatus('anonymous')
      })
  }, [])

  useEffect(() => {
    const onExpired = (e: Event) => {
      setUser(null)
      setStatus('anonymous')
      queryClient.clear()
      toast.error((e as CustomEvent<string>).detail || 'Your session has expired. Please sign in again.')
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired)
  }, [queryClient])

  const acceptToken = useCallback((res: TokenResponse) => {
    tokenStore.set(res.access_token)
    setUser(res.user)
    setStatus('authenticated')
  }, [])

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await authApi.login({ email, password })
      queryClient.clear()
      acceptToken(res)
      return res.user
    },
    [acceptToken, queryClient],
  )

  const register = useCallback(
    async (full_name: string, email: string, password: string) => {
      const res = await authApi.register({ full_name, email, password })
      queryClient.clear()
      acceptToken(res)
      return res.user
    },
    [acceptToken, queryClient],
  )

  const logout = useCallback(async () => {
    try {
      await authApi.logout() // revokes every token issued to this user server-side
    } catch {
      /* already invalid — sign out locally regardless */
    }
    tokenStore.clear()
    queryClient.clear()
    setUser(null)
    setStatus('anonymous')
  }, [queryClient])

  const value = useMemo(
    () => ({ user, status, login, register, logout, setUser, acceptToken }),
    [user, status, login, register, logout, acceptToken],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
