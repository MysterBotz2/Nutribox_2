import { apiClient } from './client'
import type { NutritionCoachRequest, NutritionCoachResponse } from './types'

export const coachApi = {
  ask: (request: NutritionCoachRequest, timezone: string): Promise<NutritionCoachResponse> =>
    apiClient.post(`/api/ai/coach?${new URLSearchParams({ timezone })}`, request),
}
