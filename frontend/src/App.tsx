import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '@/store/auth-context'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { AppLayout } from '@/components/AppLayout'
import { LoginPage } from '@/pages/auth/LoginPage'
import { SignupPage } from '@/pages/auth/SignupPage'
import { DashboardPage } from '@/pages/app/DashboardPage'
import { TransactionsPage } from '@/pages/app/TransactionsPage'
import { AnalysisPage } from '@/pages/app/AnalysisPage'
import { AlertsPage } from '@/pages/app/AlertsPage'
import { SettingsPage } from '@/pages/app/SettingsPage'

export function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        {/* Protected — all nested inside AppLayout */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/transactions" element={<TransactionsPage />} />
            <Route path="/analysis" element={<AnalysisPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Route>

        {/* Default: go to dashboard (ProtectedRoute handles unauth redirect) */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  )
}
