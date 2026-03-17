import { apiClient } from './client'

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

export function runAnalysisApi(analysis_type: string) {
  return apiClient.post<AnalysisRun>('/api/v1/analysis/run', { analysis_type })
}

export function getAnalysisResultsApi(params: {
  analysis_type?: string
  status?: string
  page?: number
}) {
  return apiClient.get<PaginatedResponse<AnalysisRun>>('/api/v1/analysis/results', { params })
}

export function getAnalysisResultApi(id: string) {
  return apiClient.get<AnalysisRun>(`/api/v1/analysis/results/${id}/`)
}
