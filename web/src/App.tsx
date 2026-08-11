import { Navigate, Route, Routes } from 'react-router-dom'

import { useAuth } from './auth/useAuth'
import { AppShell } from './pages/AppShell'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'

function ProtectedRoute() {
  const { isAuthenticated, isChecking } = useAuth()
  if (isChecking) return <main className="status-page">Checking authentication…</main>
  return isAuthenticated ? <AppShell /> : <Navigate to="/login" replace />
}

function HomeRedirect() {
  const { isAuthenticated, isChecking } = useAuth()
  if (isChecking) return <main className="status-page">Checking authentication…</main>
  return <Navigate to={isAuthenticated ? '/app' : '/login'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/app" element={<ProtectedRoute />} />
      <Route path="*" element={<HomeRedirect />} />
    </Routes>
  )
}
