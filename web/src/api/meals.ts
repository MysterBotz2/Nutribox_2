import { apiClient } from './client'
import type { MealCreateRequest, MealListResponse, MealResponse } from './types'

export const mealsApi = {
  list: (limit: number, offset: number): Promise<MealListResponse> =>
    apiClient.get(`/api/meals?${new URLSearchParams({ limit: String(limit), offset: String(offset) })}`),
  listRecent: (limit = 3): Promise<MealListResponse> => apiClient.get(`/api/meals?limit=${limit}&offset=0`),
  get: (mealId: number): Promise<MealResponse> => apiClient.get(`/api/meals/${mealId}`),
  create: (requestBody: MealCreateRequest): Promise<MealResponse> => apiClient.post('/api/meals', requestBody),
}
