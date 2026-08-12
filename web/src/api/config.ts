export function resolveApiBaseUrl(configuredValue: string | undefined): string {
  return configuredValue?.trim().replace(/\/$/, '') ?? ''
}

// Empty means same-origin requests such as /api/users/me.
export const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL)
