import { apiClient } from './client'

export interface Transaction {
  id: string
  vendor: string
  amount: string // decimal string
  date: string // YYYY-MM-DD
  category: string
  description: string
  created_at: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface TransactionImportRow {
  vendor: string
  amount: string
  date: string
  category?: string
  description?: string
}

export function getTransactionsApi(params: Record<string, string>) {
  return apiClient.get<PaginatedResponse<Transaction>>('/api/v1/transactions/', { params })
}

export function importTransactionsApi(transactions: TransactionImportRow[]) {
  return apiClient.post<{ imported: number }>('/api/v1/transactions/import', { transactions })
}

export function deleteTransactionApi(id: string) {
  return apiClient.delete<void>(`/api/v1/transactions/${id}/delete`)
}
