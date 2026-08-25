import { apiClient } from './client'
import type { MealAnalysisResponse, MealAnalysisSelectionRequest } from './types'

export const scanApi = {
  analyze(file: File, weightGrams: string): Promise<MealAnalysisResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('weight_grams', weightGrams)
    return apiClient.requestMultipart('/api/meals/analyze', formData, true)
  },
  selectCandidate(sessionId: number, request: MealAnalysisSelectionRequest): Promise<MealAnalysisResponse> {
    return apiClient.post(`/api/meals/analysis-sessions/${sessionId}/selections`, request)
  },
}
