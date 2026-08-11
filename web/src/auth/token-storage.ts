const ACCESS_TOKEN_KEY = 'nutribox.access_token'

export function getSessionToken(): string | null {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY)
}

export function storeSessionToken(token: string): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, token)
}

export function clearSessionToken(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY)
}
