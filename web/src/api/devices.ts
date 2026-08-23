import { apiClient } from './client'
import type { PairedDeviceListResponse, PairedDeviceResponse } from './types'

export const devicesApi = {
  list: (): Promise<PairedDeviceListResponse> => apiClient.get('/api/users/me/devices'),
  pair: (pairing_code: string): Promise<PairedDeviceResponse> => apiClient.post('/api/users/me/devices/pair', { pairing_code }),
  remove: (deviceId: number): Promise<void> => apiClient.delete(`/api/users/me/devices/${deviceId}`),
}
