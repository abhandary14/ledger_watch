import axios from 'axios'

// Access token lives in memory only to reduce XSS risk.
// Refresh token lives in sessionStorage by default (cleared on window close).
// When "keep me signed in" is chosen it is stored in localStorage instead.
let accessToken: string | null = null

function getStoredRefresh(): { token: string; storage: Storage } | null {
  const session = sessionStorage.getItem('refresh_token')
  if (session) return { token: session, storage: sessionStorage }
  const local = localStorage.getItem('refresh_token')
  if (local) return { token: local, storage: localStorage }
  return null
}

export function clearStoredRefresh(): void {
  sessionStorage.removeItem('refresh_token')
  localStorage.removeItem('refresh_token')
}

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

// Prevents multiple simultaneous refresh calls when several requests 401 at once.
let refreshPromise: Promise<string> | null = null

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach access token to every outgoing request.
apiClient.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers['Authorization'] = `Bearer ${accessToken}`
  }
  return config
})

async function doTokenRefresh(): Promise<string> {
  const stored = getStoredRefresh()
  if (!stored) throw new Error('No refresh token stored')

  // Use plain axios so this request bypasses the interceptor (avoids recursion).
  const { data } = await axios.post<{ access: string; refresh?: string }>(
    `${BASE_URL}/api/v1/auth/token/refresh`,
    { refresh: stored.token },
    { timeout: 10_000 },
  )

  setAccessToken(data.access)
  // simplejwt rotates the refresh token — write back to the same storage.
  if (data.refresh) {
    stored.storage.setItem('refresh_token', data.refresh)
  }
  return data.access
}

// On 401: refresh access token, retry the original request once.
// On second 401 (or missing refresh token): clear session and go to /login.
apiClient.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error)) return Promise.reject(error)

    type RetryableConfig = typeof error.config & { _retry?: boolean }
    const originalRequest = error.config as RetryableConfig | undefined

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        if (!refreshPromise) {
          refreshPromise = doTokenRefresh().finally(() => {
            refreshPromise = null
          })
        }

        const newToken = await refreshPromise
        originalRequest.headers = originalRequest.headers ?? {}
        originalRequest.headers['Authorization'] = `Bearer ${newToken}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        // Only clear session for actual auth failures (bad/expired refresh token)
        // or when no token exists. Network errors and 5xx should not force logout.
        const noToken =
          refreshError instanceof Error &&
          refreshError.message === 'No refresh token stored'
        const isAuthFailure =
          axios.isAxiosError(refreshError) && refreshError.response?.status === 401
        if (noToken || isAuthFailure) {
          setAccessToken(null)
          clearStoredRefresh()
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  },
)
