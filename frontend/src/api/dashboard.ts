import { apiClient } from './client'

export interface Transaction {
  id: string
  vendor: string
  amount: string
  date: string
  category: string
  description: string
  created_at: string
}

export interface Alert {
  id: string
  alert_type: string
  severity: 'HIGH' | 'MEDIUM' | 'LOW'
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED'
  message: string
  created_at: string
}

export interface AnalysisRun {
  id: string
  analysis_type: string
  status: 'PENDING' | 'SUCCEEDED' | 'FAILED'
  run_time: string | null
  created_at: string
  results_summary: Record<string, unknown> | null
  error_message: string | null
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export function getTransactionsApi(params: Record<string, string>) {
  return apiClient.get<PaginatedResponse<Transaction>>('/api/v1/transactions/', { params })
}

export function getOpenAlertsApi(pageSize = 100) {
  return apiClient.get<PaginatedResponse<Alert>>('/api/v1/alerts/', {
    params: { status: 'OPEN', page_size: String(pageSize) },
  })
}

export function getLatestAnalysisApi() {
  return apiClient.get<PaginatedResponse<AnalysisRun>>('/api/v1/analysis/results', {
    params: { page_size: '1' },
  })
}

export function acknowledgeAlertApi(id: string) {
  return apiClient.post<Alert>(`/api/v1/alerts/${id}/acknowledge`)
}
