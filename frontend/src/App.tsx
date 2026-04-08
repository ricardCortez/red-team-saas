import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuthStore } from './store/authStore'
import MainLayout from './layouts/MainLayout'
import LoginForm from './components/Auth/LoginForm'
import RegisterForm from './components/Auth/RegisterForm'
import DashboardPage from './pages/DashboardPage'
import ProjectsPage from './pages/ProjectsPage'
import TargetsPage from './pages/TargetsPage'
import ScansPage from './pages/ScansPage'
import FindingsPage from './pages/FindingsPage'
import ReportsPage from './pages/ReportsPage'
import ToolsPage from './pages/ToolsPage'
import CompliancePage from './pages/CompliancePage'
import ThreatIntelPage from './pages/ThreatIntelPage'
import NotificationsPage from './pages/NotificationsPage'
import SettingsPage from './pages/SettingsPage'
import PhishingPage from './pages/PhishingPage'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

export default function App() {
  const { isAuthenticated, fetchUser } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated) fetchUser()
  }, [isAuthenticated, fetchUser])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={isAuthenticated ? <Navigate to="/" /> : <LoginForm />} />
        <Route path="/register" element={isAuthenticated ? <Navigate to="/" /> : <RegisterForm />} />
        <Route path="/" element={<PrivateRoute><MainLayout /></PrivateRoute>}>
          <Route index element={<DashboardPage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="targets" element={<TargetsPage />} />
          <Route path="scans" element={<ScansPage />} />
          <Route path="phishing" element={<PhishingPage />} />
          <Route path="findings" element={<FindingsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="tools" element={<ToolsPage />} />
          <Route path="compliance" element={<CompliancePage />} />
          <Route path="threat-intel" element={<ThreatIntelPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  )
}
