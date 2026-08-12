import { apiClient } from './client'
import type { MealAnalysisResponse } from './types'

export const scanApi = {
  analyze(file: File, weightGrams: string): Promise<MealAnalysisResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('weight_grams', weightGrams)
    return apiClient.requestMultipart('/api/meals/analyze', formData)
  },
}
