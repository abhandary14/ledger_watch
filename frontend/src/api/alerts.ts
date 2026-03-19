import { apiClient } from './client'

export interface Alert {
  id: string
  alert_type: string
  severity: 'HIGH' | 'MEDIUM' | 'LOW'
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED'
  message: string
  created_at: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export function getAlertsApi(params: {
  alert_type?: string
  severity?: string
  status?: string
  ordering?: string
  page?: number
  page_size?: number | string
}) {
  return apiClient.get<PaginatedResponse<Alert>>('/api/v1/alerts/', { params })
}

export function acknowledgeAlertApi(id: string) {
  return apiClient.post<Alert>(`/api/v1/alerts/${id}/acknowledge`)
}

export function resolveAlertApi(id: string) {
  return apiClient.post<Alert>(`/api/v1/alerts/${id}/resolve`)
}

export function reopenAlertApi(id: string) {
  return apiClient.post<Alert>(`/api/v1/alerts/${id}/reopen`)
}

export function deleteAlertApi(id: string) {
  return apiClient.delete<void>(`/api/v1/alerts/${id}/delete`)
}
