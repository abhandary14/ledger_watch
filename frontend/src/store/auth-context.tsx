import {
  createContext,
  useCallback,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import axios from 'axios'
import { setAccessToken } from '@/api/client'
import { getMeApi, loginApi, logoutApi, registerApi, type MeResponse } from '@/api/auth'

interface AuthContextValue {
  user: MeResponse | null
  isAuthenticated: boolean
  /** True while the initial session-restore check is in flight. */
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  register: (email: string, password: string, orgName: string) => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // On mount, restore session from the stored refresh token.
  // The Axios response interceptor handles getting a fresh access token
  // when /me returns 401, so we just call /me directly.
  useEffect(() => {
    const restore = async () => {
      const storedRefresh = localStorage.getItem('refresh_token')
      if (!storedRefresh) {
        setIsLoading(false)
        return
      }
      try {
        const { data } = await getMeApi()
        setUser(data)
      } catch (err) {
        // Only clear tokens for actual auth failures. Transient network errors
        // or 5xx responses should not log the user out.
        const status = axios.isAxiosError(err) ? err.response?.status : undefined
        if (status === 401 || status === 403) {
          localStorage.removeItem('refresh_token')
          setAccessToken(null)
        }
      } finally {
        setIsLoading(false)
      }
    }

    restore()
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const { data: tokens } = await loginApi({ email, password })
    setAccessToken(tokens.access)
    localStorage.setItem('refresh_token', tokens.refresh)
    const { data: me } = await getMeApi()
    setUser(me)
  }, [])

  const logout = useCallback(async () => {
    const refresh = localStorage.getItem('refresh_token')
    if (refresh) {
      try {
        await logoutApi(refresh)
      } catch {
        // Blacklist failure is non-fatal; we still clear local state.
      }
    }
    setAccessToken(null)
    localStorage.removeItem('refresh_token')
    setUser(null)
  }, [])

  const register = useCallback(
    async (email: string, password: string, orgName: string) => {
      const { data: tokens } = await registerApi({
        email,
        password,
        organization_name: orgName,
      })
      setAccessToken(tokens.access)
      localStorage.setItem('refresh_token', tokens.refresh)
      const { data: me } = await getMeApi()
      setUser(me)
    },
    [],
  )

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: user !== null,
        isLoading,
        login,
        logout,
        register,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
