import { apiClient } from './client'
import type { ChatConversationListResponse, ChatConversationResponse, ChatRequest, ChatResponse } from './types'
export const chatApi = {
  list: () => apiClient.get<ChatConversationListResponse>('/api/ai/conversations'),
  get: (id: number) => apiClient.get<ChatConversationResponse>(`/api/ai/conversations/${id}`),
  send: (body: ChatRequest) => apiClient.post<ChatResponse>('/api/ai/chat', body),
}
