import { Routes, Route, Navigate } from 'react-router-dom'
import { useIsAuthenticated, useRole } from '@/stores/authStore'

// Layout
import { AppLayout } from '@/components/layout/AppLayout'

// Auth screens
import { Login } from '@/screens/auth/Login'

// Lawyer screens
import { LawyerDashboard } from '@/screens/lawyer/Dashboard'
import { CaseNew } from '@/screens/lawyer/CaseNew'
import { CaseDetail } from '@/screens/lawyer/CaseDetail'
import { PaymentScreen } from '@/screens/lawyer/PaymentScreen'

// Accounts screens
import { AccountsQueue } from '@/screens/accounts/AccountsQueue'
import { AccountsReview } from '@/screens/accounts/AccountsReview'

// Registrar screens
import { RegistrarQueue } from '@/screens/registrar/RegistrarQueue'
import { RegistrarReview } from '@/screens/registrar/RegistrarReview'

/** Redirect to the right dashboard based on role. */
function DashboardRedirect() {
  const role = useRole()
  if (role === 'accounts_dept') return <Navigate to="/accounts/queue" replace />
  if (role === 'registrar')     return <Navigate to="/registrar/queue" replace />
  return <LawyerDashboard />
}

/** Guard: redirect to /login if not authenticated. */
function RequireAuth({ children }: { children: React.ReactNode }) {
  const auth = useIsAuthenticated()
  return auth ? <>{children}</> : <Navigate to="/login" replace />
}

/** Guard: redirect to /dashboard if already authenticated. */
function RequireGuest({ children }: { children: React.ReactNode }) {
  const auth = useIsAuthenticated()
  return auth ? <Navigate to="/dashboard" replace /> : <>{children}</>
}

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={
        <RequireGuest><Login /></RequireGuest>
      } />

      {/* Protected — all wrapped in AppLayout */}
      <Route element={
        <RequireAuth><AppLayout /></RequireAuth>
      }>
        <Route path="/dashboard"          element={<DashboardRedirect />} />

        {/* Lawyer routes */}
        <Route path="/cases"              element={<LawyerDashboard />} />
        <Route path="/cases/new"          element={<CaseNew />} />
        <Route path="/cases/:caseId"      element={<CaseDetail />} />
        <Route path="/cases/:caseId/payment" element={<PaymentScreen />} />

        {/* Accounts routes */}
        <Route path="/accounts/queue"           element={<AccountsQueue />} />
        <Route path="/accounts/review/:caseId"  element={<AccountsReview />} />

        {/* Registrar routes */}
        <Route path="/registrar/queue"          element={<RegistrarQueue />} />
        <Route path="/registrar/review/:caseId" element={<RegistrarReview />} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>

      {/* Root redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
