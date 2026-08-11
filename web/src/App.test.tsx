import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'

import App from './App'
import { AuthProvider } from './auth/AuthContext'
import { clearSessionToken, storeSessionToken } from './auth/token-storage'

function renderRoute(path: string) {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[path]}><AuthProvider><App /></AuthProvider></MemoryRouter></QueryClientProvider>)
}

afterEach(() => { clearSessionToken(); vi.unstubAllGlobals() })

it('redirects unauthenticated app access to login', async () => {
  renderRoute('/app')
  expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
})

it('renders the authenticated shell after current-user loading', async () => {
  storeSessionToken('token')
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 1, email: 'test@example.com', first_name: 'Test', last_name: 'User', is_active: true, created_at: '2026-01-01T00:00:00Z' }), { headers: { 'Content-Type': 'application/json' } })))
  renderRoute('/app')
  expect(await screen.findByRole('heading', { name: 'Welcome, Test' })).toBeInTheDocument()
})
