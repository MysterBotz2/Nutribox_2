import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'

import App from './App'
import { AuthProvider } from './auth/AuthContext'
import { clearSessionToken, storeSessionToken } from './auth/token-storage'

function renderRoute(path: string) {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[path]}><AuthProvider><App /></AuthProvider></MemoryRouter></QueryClientProvider>)
}

afterEach(() => { cleanup(); clearSessionToken(); vi.unstubAllGlobals() })

it.each(['/app/meals', '/app/progress'])('redirects unauthenticated protected route %s to login', async (path) => {
  renderRoute(path)
  expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
})

it('renders the authenticated shell after current-user loading', async () => {
  storeSessionToken('token')
  vi.stubGlobal('fetch', vi.fn().mockImplementation((input: string) => {
    if (input.includes('/api/users/me') && !input.includes('/profile')) return Promise.resolve(new Response(JSON.stringify({ id: 1, email: 'test@example.com', first_name: 'Test', last_name: 'User', is_active: true, created_at: '2026-01-01T00:00:00Z' }), { headers: { 'Content-Type': 'application/json' } }))
    if (input.includes('/api/progress/today')) return Promise.resolve(new Response(JSON.stringify({ date: '2026-08-11', meal_count: 0, totals: { calories: '0.000', protein_g: '0.000', carbohydrates_g: '0.000', fat_g: '0.000', fiber_g: '0.000' } }), { headers: { 'Content-Type': 'application/json' } }))
    if (input.includes('/api/progress/target-status')) return Promise.resolve(new Response(JSON.stringify({ date: '2026-08-11', meal_count: 0, consumed: { calories: '0.000', protein_g: '0.000', carbohydrates_g: '0.000', fat_g: '0.000', fiber_g: '0.000' }, targets: null, remaining: null, percent_of_target: null }), { headers: { 'Content-Type': 'application/json' } }))
    return Promise.resolve(new Response(JSON.stringify({ meals: [], limit: 3, offset: 0 }), { headers: { 'Content-Type': 'application/json' } }))
  }))
  renderRoute('/app')
  expect(await screen.findByRole('heading', { name: 'Today’s recorded nutrition' })).toBeInTheDocument()
})
