import { afterEach, expect, it, vi } from 'vitest'

import { clearSessionToken, storeSessionToken } from '../auth/token-storage'
import { devicesApi } from './devices'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

afterEach(() => {
  clearSessionToken()
  vi.unstubAllGlobals()
})

it('pairs using the authenticated client and exact six-digit request body', async () => {
  storeSessionToken('test-access-token')
  const fetchMock = vi.fn().mockResolvedValue(jsonResponse({
    id: 7, name: 'Kitchen Pi', device_type: 'nutribox_pi', paired_at: '2026-08-26T00:00:00Z', last_seen_at: null,
  }, 201))
  vi.stubGlobal('fetch', fetchMock)

  await devicesApi.pair('123456')

  const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
  expect(url).toContain('/api/users/me/devices/pair')
  expect(new Headers(init.headers).get('Authorization')).toBe('Bearer test-access-token')
  expect(new Headers(init.headers).get('Content-Type')).toBe('application/json')
  expect(init.body).toBe(JSON.stringify({ pairing_code: '123456' }))
})

it('revokes using the returned device id path', async () => {
  storeSessionToken('test-access-token')
  const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
  vi.stubGlobal('fetch', fetchMock)

  await devicesApi.remove(42)

  expect(fetchMock.mock.calls[0][0]).toContain('/api/users/me/devices/42')
  expect(new Headers((fetchMock.mock.calls[0][1] as RequestInit).headers).get('Authorization')).toBe('Bearer test-access-token')
})
