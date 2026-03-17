import { apiClient } from './client'
import type { MeResponse } from './auth'

export function updateProfileApi(data: { first_name?: string; last_name?: string }) {
  return apiClient.patch<MeResponse>('/api/v1/auth/me', data)
}

export function changePasswordApi(data: { current_password: string; new_password: string }) {
  return apiClient.post<void>('/api/v1/auth/change-password', data)
}

export function updateOrganizationApi(orgId: string, data: { name: string }) {
  return apiClient.patch<{ id: string; name: string; created_at: string }>(
    `/api/v1/organizations/${orgId}/`,
    data,
  )
}
