import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '@/store/auth-context'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { OwnerRoute } from '@/components/OwnerRoute'
import { AppLayout } from '@/components/AppLayout'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { LoginPage } from '@/pages/auth/LoginPage'
import { SignupPage } from '@/pages/auth/SignupPage'
import { DashboardPage } from '@/pages/app/DashboardPage'
import { TransactionsPage } from '@/pages/app/TransactionsPage'
import { AnalysisPage } from '@/pages/app/AnalysisPage'
import { AlertsPage } from '@/pages/app/AlertsPage'
import { SettingsPage } from '@/pages/app/SettingsPage'
import { ManageOrgPage } from '@/pages/app/ManageOrgPage'
import { OrgDirectoryPage } from '@/pages/app/OrgDirectoryPage'
import { DocsPage } from '@/pages/app/DocsPage'

export function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        {/* Protected — all nested inside AppLayout */}
        <Route element={<ProtectedRoute />}>
          <Route element={<ErrorBoundary><AppLayout /></ErrorBoundary>}>
            <Route path="/dashboard" element={<ErrorBoundary><DashboardPage /></ErrorBoundary>} />
            <Route path="/transactions" element={<ErrorBoundary><TransactionsPage /></ErrorBoundary>} />
            <Route path="/analysis" element={<ErrorBoundary><AnalysisPage /></ErrorBoundary>} />
            <Route path="/alerts" element={<ErrorBoundary><AlertsPage /></ErrorBoundary>} />
            <Route path="/settings" element={<ErrorBoundary><SettingsPage /></ErrorBoundary>} />
            <Route path="/org-directory" element={<ErrorBoundary><OrgDirectoryPage /></ErrorBoundary>} />
            <Route path="/docs" element={<ErrorBoundary><DocsPage /></ErrorBoundary>} />

            {/* Owner-only routes */}
            <Route element={<OwnerRoute />}>
              <Route path="/manage-org" element={<ErrorBoundary><ManageOrgPage /></ErrorBoundary>} />
            </Route>
          </Route>
        </Route>

        {/* Default: go to dashboard (ProtectedRoute handles unauth redirect) */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  )
}
