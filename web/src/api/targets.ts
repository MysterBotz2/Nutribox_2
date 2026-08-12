import { apiClient } from './client'
import type { NutritionTargetResponse, NutritionTargetUpdateRequest } from './types'

export const targetsApi = {
  get: (): Promise<NutritionTargetResponse> => apiClient.get('/api/users/me/targets'),
  replace: (targets: NutritionTargetUpdateRequest): Promise<NutritionTargetResponse> =>
    apiClient.put('/api/users/me/targets', targets),
}
