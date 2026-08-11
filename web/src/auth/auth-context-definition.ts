import { createContext } from 'react'

import type { PublicUser, UserRegistrationRequest } from '../api/types'

export type AuthContextValue = {
  user: PublicUser | undefined
  isChecking: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (request: UserRegistrationRequest) => Promise<PublicUser>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)
