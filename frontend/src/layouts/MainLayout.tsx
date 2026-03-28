import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from '../components/Common/Sidebar'
import Navbar from '../components/Common/Navbar'
import { useWebSocket } from '../hooks/useWebSocket'

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/projects': 'Projects',
  '/targets': 'Targets',
  '/scans': 'Scans',
  '/findings': 'Findings',
  '/reports': 'Reports',
  '/tools': 'Tools',
  '/compliance': 'Compliance',
  '/threat-intel': 'Threat Intelligence',
  '/notifications': 'Notifications',
  '/settings': 'Settings',
}

export default function MainLayout() {
  const location = useLocation()
  const title = pageTitles[location.pathname] || 'Red Team SaaS'

  // Connect WebSocket for real-time updates
  useWebSocket()

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 ml-64">
        <Navbar title={title} />
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
