import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from '../components/Common/Sidebar'
import Navbar from '../components/Common/Navbar'
import { useWebSocket } from '../hooks/useWebSocket'
import AIChatButton from '../components/AI/AIChatButton'
import AIChat from '../components/AI/AIChat'
import { useAIStore } from '../store/aiStore'
import { useEffect } from 'react'

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
  '/test-lab': 'Test Lab',
  '/settings': 'Settings',
  '/phishing': 'Phishing',
}

export default function MainLayout() {
  const location = useLocation()
  const title = pageTitles[location.pathname] || 'Red Team SaaS'
  const { setPageContext } = useAIStore()

  useWebSocket()

  useEffect(() => {
    setPageContext(title)
  }, [title, setPageContext])

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 ml-64">
        <Navbar title={title} />
        <main className="p-6">
          <Outlet />
        </main>
      </div>
      <AIChatButton />
      <AIChat />
    </div>
  )
}
