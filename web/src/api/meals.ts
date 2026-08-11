import { apiClient } from './client'
import type { MealListResponse } from './types'

export const mealsApi = {
  listRecent: (limit = 3): Promise<MealListResponse> => apiClient.get(`/api/meals?limit=${limit}&offset=0`),
}
