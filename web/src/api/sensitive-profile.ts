import { apiClient } from './client'
import type {
  ProfileConsentResponse,
  ProfileConsentUpdateRequest,
  SensitiveProfileResponse,
  SensitiveProfileUpdateRequest,
  OnboardingStatusResponse,
} from './types'

export const sensitiveProfileApi = {
  getConsent: (): Promise<ProfileConsentResponse> => apiClient.get('/api/users/me/profile-consent'),
  replaceConsent: (request: ProfileConsentUpdateRequest): Promise<ProfileConsentResponse> =>
    apiClient.put('/api/users/me/profile-consent', request),
  get: (): Promise<SensitiveProfileResponse> => apiClient.get('/api/users/me/sensitive-profile'),
  replace: (request: SensitiveProfileUpdateRequest): Promise<SensitiveProfileResponse> =>
    apiClient.put('/api/users/me/sensitive-profile', request),
  getOnboardingStatus: (): Promise<OnboardingStatusResponse> =>
    apiClient.get('/api/users/me/onboarding-status'),
}
