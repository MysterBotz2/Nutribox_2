import { apiClient } from './client'
import type { NutritionProfileResponse, NutritionProfileUpdateRequest } from './types'

export const profileApi = {
  get: (): Promise<NutritionProfileResponse> => apiClient.get('/api/users/me/profile'),
  replace: (profile: NutritionProfileUpdateRequest): Promise<NutritionProfileResponse> =>
    apiClient.put('/api/users/me/profile', profile),
}
