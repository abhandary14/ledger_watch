import { apiClient } from './client'

export interface OrgMember {
  id: string
  email: string
  first_name: string
  last_name: string
  role: 'owner' | 'admin' | 'employee'
  created_at: string
}

export interface CreateMemberPayload {
  email: string
  password: string
  role: 'admin' | 'employee'
  first_name?: string
  last_name?: string
}

export function getOrgMembersApi() {
  return apiClient.get<OrgMember[]>('/api/v1/organizations/members/')
}

export function createOrgMemberApi(data: CreateMemberPayload) {
  return apiClient.post<OrgMember>('/api/v1/organizations/members/', data)
}

export function updateMemberRoleApi(id: string, role: 'admin' | 'employee') {
  return apiClient.patch<OrgMember>(`/api/v1/organizations/members/${id}/`, { role })
}

export function getOrgDirectoryApi() {
  return apiClient.get<OrgMember[]>('/api/v1/organizations/directory/')
}

export function getSecurityChallengeApi() {
  return apiClient.post<{ challenge: string }>('/api/v1/organizations/security-challenge/')
}

export function deleteMemberApi(id: string, password: string, challenge: string) {
  return apiClient.delete<void>(`/api/v1/organizations/members/${id}/`, {
    data: { password, challenge },
  })
}

export function transferOwnershipApi(newOwnerId: string, password: string, challenge: string) {
  return apiClient.post<{ transferred: boolean }>('/api/v1/organizations/transfer-ownership/', {
    new_owner_id: newOwnerId,
    password,
    challenge,
  })
}
