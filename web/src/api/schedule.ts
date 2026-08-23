import { apiClient } from './client'
import type { ScheduledMealCreateRequest, ScheduledMealListResponse, ScheduledMealResponse, ScheduledMealUpdateRequest } from './types'
export const scheduleApi = {
  list: () => apiClient.get<ScheduledMealListResponse>('/api/scheduled-meals?limit=50&offset=0'),
  create: (body: ScheduledMealCreateRequest) => apiClient.post<ScheduledMealResponse>('/api/scheduled-meals', body),
  update: (id: number, body: ScheduledMealUpdateRequest) => apiClient.put<ScheduledMealResponse>(`/api/scheduled-meals/${id}`, body),
  remove: (id: number) => apiClient.delete<void>(`/api/scheduled-meals/${id}`),
}
