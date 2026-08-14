import { useContext } from 'react'

import { AuthContext } from './auth-context-definition'
import type { AuthContextValue } from './auth-context-definition'

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider.')
  return value
}
