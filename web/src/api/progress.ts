import { apiClient } from './client'
import type { DailyProgressResponse, TargetStatusResponse } from './types'

function withTimezone(path: string, timezone: string): string {
  return `${path}?${new URLSearchParams({ timezone }).toString()}`
}

export const progressApi = {
  getToday: (timezone: string): Promise<DailyProgressResponse> =>
    apiClient.get(withTimezone('/api/progress/today', timezone)),
  getTargetStatus: (timezone: string): Promise<TargetStatusResponse> =>
    apiClient.get(withTimezone('/api/progress/target-status', timezone)),
}
