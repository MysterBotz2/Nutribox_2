import { API_BASE_URL } from './config'
import type { AccessTokenResponse, PublicUser, UserRegistrationRequest } from './types'
import { getSessionToken } from '../auth/token-storage'

export class ApiError extends Error {
  readonly status: number
  readonly detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

let unauthorizedHandler: (() => void) | undefined

export function setUnauthorizedHandler(handler: (() => void) | undefined): void {
  unauthorizedHandler = handler
}

export function normalizeApiError(status: number, payload: unknown): ApiError {
  const detail =
    typeof payload === 'object' && payload !== null && 'detail' in payload
      ? typeof payload.detail === 'string'
        ? payload.detail
        : 'Please correct the highlighted request fields.'
      : 'The backend returned an unexpected response.'
  return new ApiError(status, detail)
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  options: { authenticated?: boolean } = {},
): Promise<T> {
  const headers = new Headers(init.headers)
  if (options.authenticated) {
    const token = getSessionToken()
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, 'Unable to reach the Nutri-Box backend.')
  }

  const payload: unknown = await response.json().catch(() => undefined)
  if (!response.ok) {
    const error = normalizeApiError(response.status, payload)
    if (response.status === 401 && options.authenticated) unauthorizedHandler?.()
    throw error
  }
  return payload as T
}

export const apiClient = {
  register(requestBody: UserRegistrationRequest): Promise<PublicUser> {
    return request('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    })
  },

  login(email: string, password: string): Promise<AccessTokenResponse> {
    const body = new URLSearchParams({ username: email, password })
    return request('/api/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    })
  },

  getCurrentUser(): Promise<PublicUser> {
    return request('/api/users/me', {}, { authenticated: true })
  },

  get<T>(path: string): Promise<T> {
    return request(path, {}, { authenticated: true })
  },

  put<T>(path: string, requestBody: unknown): Promise<T> {
    return request(path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    }, { authenticated: true })
  },

  requestMultipart<T>(path: string, formData: FormData, authenticated = false): Promise<T> {
    return request(path, { method: 'POST', body: formData }, { authenticated })
  },
}
