import { Navigate, Route, Routes } from 'react-router-dom'

import { useAuth } from './auth/useAuth'
import { AppLayout } from './layouts/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { CoachPage } from './pages/CoachPage'
import { LoginPage } from './pages/LoginPage'
import { MealDetailPage } from './pages/MealDetailPage'
import { MealsPage } from './pages/MealsPage'
import { ProfilePage } from './pages/ProfilePage'
import { ProgressPage } from './pages/ProgressPage'
import { RegisterPage } from './pages/RegisterPage'
import { ScanPage } from './pages/ScanPage'
import { TargetsPage } from './pages/TargetsPage'
import { AiPage } from './pages/AiPage'
import { ChatPage } from './pages/ChatPage'
import { SchedulePage } from './pages/SchedulePage'
import { DevicesPage } from './pages/DevicesPage'

function ProtectedRoute() {
  const { isAuthenticated, isChecking } = useAuth()
  if (isChecking) return <main className="status-page">Checking authentication…</main>
  return isAuthenticated ? <AppLayout /> : <Navigate to="/login" replace />
}

function HomeRedirect() {
  const { isAuthenticated, isChecking } = useAuth()
  if (isChecking) return <main className="status-page">Checking authentication…</main>
  return <Navigate to={isAuthenticated ? '/app/dashboard' : '/login'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/app" element={<ProtectedRoute />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="meals" element={<MealsPage />} />
        <Route path="meals/:mealId" element={<MealDetailPage />} />
        <Route path="progress" element={<ProgressPage />} />
        <Route path="schedule" element={<SchedulePage />} />
        <Route path="scan" element={<ScanPage />} />
        <Route path="coach" element={<CoachPage />} />
        <Route path="ai" element={<AiPage />}><Route index element={<Navigate to="coach" replace />} /><Route path="coach" element={<CoachPage />} /><Route path="chat" element={<ChatPage />} /></Route>
        <Route path="profile" element={<ProfilePage />} />
        <Route path="devices" element={<DevicesPage />} />
        <Route path="targets" element={<TargetsPage />} />
      </Route>
      <Route path="*" element={<HomeRedirect />} />
    </Routes>
  )
}
