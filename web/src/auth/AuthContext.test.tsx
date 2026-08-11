import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'

import { AuthProvider } from './AuthContext'
import { useAuth } from './useAuth'
import { clearSessionToken, getSessionToken, storeSessionToken } from './token-storage'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function renderAuth(ui: React.ReactNode) {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><AuthProvider>{ui}</AuthProvider></QueryClientProvider>)
}

function Harness() {
  const { login, logout, user } = useAuth()
  return <><button onClick={() => void login('test@example.com', 'password-1234')}>Login</button><button onClick={logout}>Logout</button><p>{user?.email}</p></>
}

afterEach(() => {
  clearSessionToken()
  vi.unstubAllGlobals()
})

it('stores a token and loads /users/me after login', async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(jsonResponse({ access_token: 'new-token', token_type: 'bearer' }))
    .mockResolvedValueOnce(jsonResponse({ id: 1, email: 'test@example.com', first_name: 'Test', last_name: 'User', is_active: true, created_at: '2026-01-01T00:00:00Z' }))
  vi.stubGlobal('fetch', fetchMock)
  renderAuth(<Harness />)

  await userEvent.setup().click(screen.getByRole('button', { name: 'Login' }))
  await screen.findByText('test@example.com')
  expect(getSessionToken()).toBe('new-token')
  expect(fetchMock.mock.calls[1][0]).toContain('/api/users/me')
})

it('clears authentication after logout or a protected 401', async () => {
  storeSessionToken('old-token')
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'Could not validate credentials.' }, 401)))
  renderAuth(<Harness />)

  await waitFor(() => expect(getSessionToken()).toBeNull())
})
