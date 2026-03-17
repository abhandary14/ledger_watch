import { useContext } from 'react'
import { AuthContext } from '@/store/auth-context'

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (ctx === null) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}
