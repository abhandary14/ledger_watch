import { useContext } from 'react'
import { AuthContext } from '@/store/auth-context'

export function useAuth() {
  return useContext(AuthContext)
}
