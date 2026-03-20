import { apiClient } from './client'

export interface ReportRun {
  id: string
  organization_id: string
  generated_at: string
  report_path: string
  alert_count: number
  triggered_by: 'scheduled' | 'manual'
  status: 'PENDING' | 'SUCCEEDED' | 'FAILED'
  error_message: string | null
}

export interface NoNewAlertsResponse {
  detail: string
  report: null
}

export function generateReportApi() {
  return apiClient.post<ReportRun | NoNewAlertsResponse>('/api/v1/reports/generate')
}
