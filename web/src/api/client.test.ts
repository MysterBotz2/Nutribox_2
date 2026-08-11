import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiClient, ApiError } from './client'
import { API_BASE_URL, resolveApiBaseUrl } from './config'
import { clearSessionToken, storeSessionToken } from '../auth/token-storage'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

afterEach(() => {
  clearSessionToken()
  vi.unstubAllGlobals()
})

describe('API client', () => {
  it('uses same-origin relative requests when the API base is missing or blank', () => {
    expect(resolveApiBaseUrl(undefined)).toBe('')
    expect(resolveApiBaseUrl('   ')).toBe('')
    expect(API_BASE_URL).toBe('')
  })

  it('preserves an explicit API-origin override without a trailing slash', () => {
    expect(resolveApiBaseUrl('https://api.example.test/')).toBe('https://api.example.test')
  })

  it('sends registration as JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1 }))
    vi.stubGlobal('fetch', fetchMock)

    await apiClient.register({ email: 'test@example.com', password: 'password-1234', first_name: 'Test', last_name: 'User' })

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/json')
    expect(JSON.parse(String(init.body))).toMatchObject({ email: 'test@example.com' })
  })

  it('uses OAuth2 form encoding and maps email to username', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ access_token: 'token', token_type: 'bearer' }))
    vi.stubGlobal('fetch', fetchMock)

    await apiClient.login('test@example.com', 'password-1234')

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/x-www-form-urlencoded')
    expect(String(init.body)).toContain('username=test%40example.com')
    expect(String(init.body)).toContain('password=password-1234')
  })

  it('attaches a bearer token to protected requests', async () => {
    storeSessionToken('stored-token')
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1, email: 'test@example.com' }))
    vi.stubGlobal('fetch', fetchMock)

    await apiClient.getCurrentUser()

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer stored-token')
  })

  it.each([409, 422])('normalizes safe backend error status %i', async (status) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: status === 409 ? 'Email already exists.' : [{ msg: 'Invalid input' }] }, status)))

    await expect(apiClient.register({ email: 'test@example.com', password: 'password-1234', first_name: 'Test', last_name: 'User' }))
      .rejects.toMatchObject({ status } satisfies Partial<ApiError>)
  })
})
