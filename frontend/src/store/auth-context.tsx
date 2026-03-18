import {
  createContext,
  useCallback,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import axios from 'axios'
import { clearStoredRefresh, setAccessToken } from '@/api/client'
import { getMeApi, loginApi, logoutApi, registerApi, type MeResponse, type TokenResponse } from '@/api/auth'

interface AuthContextValue {
  user: MeResponse | null
  isAuthenticated: boolean
  /** True while the initial session-restore check is in flight. */
  isLoading: boolean
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>
  logout: () => Promise<void>
  register: (email: string, password: string, orgName: string) => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // On mount, restore session from the stored refresh token (either storage).
  // The Axios response interceptor handles getting a fresh access token
  // when /me returns 401, so we just call /me directly.
  useEffect(() => {
    const restore = async () => {
      const hasRefresh =
        sessionStorage.getItem('refresh_token') !== null ||
        localStorage.getItem('refresh_token') !== null
      if (!hasRefresh) {
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
          clearStoredRefresh()
          setAccessToken(null)
        }
      } finally {
        setIsLoading(false)
      }
    }

    restore()
  }, [])

  // Sets the in-memory access token, fetches the user, then — only on success —
  // persists the refresh token. Cleans up and rethrows on any failure so callers
  // see the error and no partial state is left behind.
  // rememberMe=true stores in localStorage (survives window close); otherwise sessionStorage.
  const bootstrapSession = useCallback(async (tokens: TokenResponse, rememberMe = false) => {
    setAccessToken(tokens.access)
    try {
      const { data: me } = await getMeApi()
      const storage = rememberMe ? localStorage : sessionStorage
      storage.setItem('refresh_token', tokens.refresh)
      setUser(me)
    } catch (err) {
      setAccessToken(null)
      setUser(null)
      throw err
    }
  }, [])

  const login = useCallback(async (email: string, password: string, rememberMe = false) => {
    const { data: tokens } = await loginApi({ email, password })
    await bootstrapSession(tokens, rememberMe)
  }, [bootstrapSession])

  const logout = useCallback(async () => {
    const refresh =
      sessionStorage.getItem('refresh_token') ?? localStorage.getItem('refresh_token')
    if (refresh) {
      try {
        await logoutApi(refresh)
      } catch {
        // Blacklist failure is non-fatal; we still clear local state.
      }
    }
    setAccessToken(null)
    clearStoredRefresh()
    setUser(null)
  }, [])

  const register = useCallback(
    async (email: string, password: string, orgName: string) => {
      const { data: tokens } = await registerApi({
        email,
        password,
        organization_name: orgName,
      })
      await bootstrapSession(tokens)
    },
    [bootstrapSession],
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
