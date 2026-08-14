import { apiClient } from './client'
import type { DailyProgressResponse, ProgressSummaryResponse, TargetStatusResponse, WeeklyProgressResponse } from './types'

function withTimezone(path: string, timezone: string): string {
  return `${path}?${new URLSearchParams({ timezone }).toString()}`
}

export const progressApi = {
  getToday: (timezone: string): Promise<DailyProgressResponse> =>
    apiClient.get(withTimezone('/api/progress/today', timezone)),
  getTargetStatus: (timezone: string): Promise<TargetStatusResponse> =>
    apiClient.get(withTimezone('/api/progress/target-status', timezone)),
  getDaily: (date: string, timezone: string): Promise<DailyProgressResponse> =>
    apiClient.get(`/api/progress/daily?${new URLSearchParams({ date, timezone })}`),
  getWeekly: (weekStart: string, timezone: string): Promise<WeeklyProgressResponse> =>
    apiClient.get(`/api/progress/weekly?${new URLSearchParams({ week_start: weekStart, timezone })}`),
  getSummary: (days: number, timezone: string): Promise<ProgressSummaryResponse> =>
    apiClient.get(`/api/progress/summary?${new URLSearchParams({ days: String(days), timezone })}`),
}
