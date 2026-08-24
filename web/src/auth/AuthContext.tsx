import { useCallback, useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import { apiClient, setUnauthorizedHandler } from '../api/client'
import { clearSessionToken, getSessionToken, storeSessionToken } from './token-storage'
import { AuthContext } from './auth-context-definition'
import type { AuthContextValue } from './auth-context-definition'
import { queryKeys } from '../api/query-keys'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient()
  const [tokenPresent, setTokenPresent] = useState(() => Boolean(getSessionToken()))
  const currentUser = useQuery({
    queryKey: queryKeys.currentUser,
    queryFn: apiClient.getCurrentUser,
    enabled: tokenPresent,
    retry: false,
  })

  const logout = useCallback(() => {
    clearSessionToken()
    setTokenPresent(false)
    queryClient.removeQueries({ queryKey: queryKeys.currentUser })
    queryClient.removeQueries({ queryKey: queryKeys.sensitiveProfile })
    queryClient.removeQueries({ queryKey: queryKeys.profileConsent })
    queryClient.removeQueries({ queryKey: queryKeys.onboardingStatus })
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
      await queryClient.fetchQuery({ queryKey: queryKeys.currentUser, queryFn: apiClient.getCurrentUser })
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
