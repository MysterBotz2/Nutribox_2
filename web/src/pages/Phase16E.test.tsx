import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'

import { storeSessionToken, clearSessionToken } from '../auth/token-storage'
import { CoachPage } from './CoachPage'

const response = {
  message: 'Review your recorded meals.\nUse this as general information only.',
  highlights: ['Today has two recorded meals.', 'Targets are optional context.'],
  provider: 'mock',
  generated_at: '2026-08-12T01:23:45Z',
}

function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }) }
function renderCoach() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><CoachPage /></MemoryRouter></QueryClientProvider>)
}
function missingSetupAndCoach(responseBody: unknown = response, status = 200) {
  return vi.fn().mockImplementation((input: string) => {
    if (input.includes('/api/users/me/profile') || input.includes('/api/users/me/targets')) return Promise.resolve(json({ detail: 'Not found.' }, 404))
    if (input.includes('/api/ai/coach')) return Promise.resolve(json(responseBody, status))
    return Promise.reject(new Error(`Unexpected request: ${input}`))
  })
}

afterEach(() => { cleanup(); clearSessionToken(); vi.unstubAllGlobals() })

it('does not submit on load and missing optional setup does not block coaching', async () => {
  const fetchMock = missingSetupAndCoach()
  vi.stubGlobal('fetch', fetchMock)
  renderCoach()
  expect(await screen.findAllByText('Not configured.')).toHaveLength(2)
  expect(screen.getByRole('link', { name: 'Set up profile' })).toHaveAttribute('href', '/app/profile')
  expect(screen.getByRole('link', { name: 'Set up nutrition targets' })).toHaveAttribute('href', '/app/targets')
  expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/api/ai/coach'))).toBe(false)
  await userEvent.setup().click(screen.getByRole('button', { name: 'Ask Coach' }))
  expect(await screen.findByText('Review your recorded meals.', { exact: false })).toBeInTheDocument()
})

it('submits the optional question through bearer-authenticated centralized API client and renders plain text', async () => {
  storeSessionToken('coach-token')
  const fetchMock = missingSetupAndCoach({ ...response, message: '<em>Use the backend response unchanged.</em>' })
  vi.stubGlobal('fetch', fetchMock)
  renderCoach()
  await userEvent.setup().type(screen.getByLabelText('Optional nutrition question'), ' What should I review? ')
  await userEvent.setup().click(screen.getByRole('button', { name: 'Ask Coach' }))
  expect(await screen.findByText('<em>Use the backend response unchanged.</em>')).toBeInTheDocument()
  expect(document.querySelector('em')).toBeNull()
  const [url, init] = fetchMock.mock.calls.find(([value]) => String(value).includes('/api/ai/coach')) as [string, RequestInit]
  expect(url).toContain(`/api/ai/coach?timezone=${encodeURIComponent(Intl.DateTimeFormat().resolvedOptions().timeZone)}`)
  expect(JSON.parse(init.body as string)).toEqual({ question: 'What should I review?' })
  expect(new Headers(init.headers).get('Authorization')).toBe('Bearer coach-token')
  expect(screen.getByText('Provider: mock')).toBeInTheDocument()
})

it('uses UTC when browser timezone detection is unavailable', async () => {
  const fetchMock = missingSetupAndCoach({ detail: 'Unavailable' }, 503)
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('Intl', { DateTimeFormat: () => { throw new Error('unsupported') } })
  renderCoach()
  await userEvent.setup().click(screen.getByRole('button', { name: 'Ask Coach' }))
  expect(await screen.findByText('The coach is temporarily unavailable. Please try again later.')).toBeInTheDocument()
  const [url] = fetchMock.mock.calls.find(([value]) => String(value).includes('/api/ai/coach')) as [string]
  expect(url).toContain('timezone=UTC')
})

it.each([
  [422, 'Please correct the highlighted request fields.'],
  [429, 'The coach is temporarily rate-limited. Please try again shortly.'],
  [502, 'The coach returned an invalid response. Please try again.'],
  [503, 'The coach is temporarily unavailable. Please try again later.'],
  [504, 'The coach request timed out. Please try again.'],
])('shows safe feedback for HTTP %i', async (status, expected) => {
  vi.stubGlobal('fetch', missingSetupAndCoach({ detail: 'Please correct the highlighted request fields.' }, status))
  renderCoach()
  await userEvent.setup().click(screen.getByRole('button', { name: 'Ask Coach' }))
  expect(await screen.findByText(expected)).toBeInTheDocument()
})
