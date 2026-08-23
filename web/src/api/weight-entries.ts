import { apiClient } from './client'
import type { WeightEntryList } from './types'

export const weightEntriesApi = {
  list: (): Promise<WeightEntryList> => apiClient.get('/api/weight-entries?limit=100&offset=0'),
}
