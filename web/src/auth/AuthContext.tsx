import { useCallback, useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { apiClient, setUnauthorizedHandler } from '../api/client'
import { clearSessionToken, getSessionToken, storeSessionToken } from './token-storage'
import { AuthContext } from './auth-context-definition'
import type { AuthContextValue } from './auth-context-definition'
const currentUserQueryKey = ['auth', 'current-user'] as const

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient()
  const [tokenPresent, setTokenPresent] = useState(() => Boolean(getSessionToken()))
  const currentUser = useQuery({
    queryKey: currentUserQueryKey,
    queryFn: apiClient.getCurrentUser,
    enabled: tokenPresent,
    retry: false,
  })

  const logout = useCallback(() => {
    clearSessionToken()
    setTokenPresent(false)
    queryClient.removeQueries({ queryKey: currentUserQueryKey })
  }, [queryClient])

  useEffect(() => {
    setUnauthorizedHandler(logout)
    return () => setUnauthorizedHandler(undefined)
  }, [logout])

  const login = useCallback(
    async (email: string, password: string) => {
      const result = await apiClient.login(email, password)
      storeSessionToken(result.access_token)
      setTokenPresent(true)
      await queryClient.fetchQuery({ queryKey: currentUserQueryKey, queryFn: apiClient.getCurrentUser })
    },
    [queryClient],
  )

  const value = useMemo<AuthContextValue>(
    () => ({
      user: currentUser.data,
      isChecking: tokenPresent && currentUser.isPending,
      isAuthenticated: Boolean(currentUser.data),
      login,
      register: apiClient.register,
      logout,
    }),
    [currentUser.data, currentUser.isPending, login, logout, tokenPresent],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
