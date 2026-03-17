import { apiClient } from './client'

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  email: string
  password: string
  organization_name: string
}

export interface TokenResponse {
  access: string
  refresh: string
}

export interface MeResponse {
  id: string
  email: string
  first_name: string
  last_name: string
  organization: {
    id: string
    name: string
  }
}

export function loginApi(payload: LoginPayload) {
  return apiClient.post<TokenResponse>('/api/v1/auth/login', payload)
}

export function registerApi(payload: RegisterPayload) {
  return apiClient.post<TokenResponse>('/api/v1/auth/register', payload)
}

export function logoutApi(refresh: string) {
  return apiClient.post<void>('/api/v1/auth/logout', { refresh })
}

export function getMeApi() {
  return apiClient.get<MeResponse>('/api/v1/auth/me')
}
