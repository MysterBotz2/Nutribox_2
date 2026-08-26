import { apiClient } from './client'
import type {
  IngredientCandidateSelectionRequest,
  IngredientVerificationRequest,
  MealAnalysisResponse,
  MealAnalysisSelectionRequest,
  PersonalRecipeSelectionRequest,
  SaveUserRecipeRequest,
  UserRecipeResponse,
} from './types'

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
  verifyIngredients(sessionId: number, componentId: string, request: IngredientVerificationRequest): Promise<MealAnalysisResponse> {
    return apiClient.put(`/api/meals/analysis-sessions/${sessionId}/components/${componentId}/ingredients`, request)
  },
  selectIngredientCandidate(sessionId: number, componentId: string, request: IngredientCandidateSelectionRequest): Promise<MealAnalysisResponse> {
    return apiClient.post(`/api/meals/analysis-sessions/${sessionId}/components/${componentId}/ingredients/selections`, request)
  },
  useRecipe(sessionId: number, componentId: string, request: PersonalRecipeSelectionRequest): Promise<MealAnalysisResponse> {
    return apiClient.post(`/api/meals/analysis-sessions/${sessionId}/components/${componentId}/use-recipe`, request)
  },
  reviewRecipe(sessionId: number, componentId: string, request: PersonalRecipeSelectionRequest): Promise<MealAnalysisResponse> {
    return apiClient.post(`/api/meals/analysis-sessions/${sessionId}/components/${componentId}/review-recipe`, request)
  },
  analyzeAsNew(sessionId: number, componentId: string): Promise<MealAnalysisResponse> {
    return apiClient.post(`/api/meals/analysis-sessions/${sessionId}/components/${componentId}/analyze-as-new`, undefined)
  },
  saveRecipe(sessionId: number, componentId: string, request?: SaveUserRecipeRequest): Promise<UserRecipeResponse> {
    return apiClient.post(`/api/meals/analysis-sessions/${sessionId}/components/${componentId}/save-recipe`, request)
  },
}
