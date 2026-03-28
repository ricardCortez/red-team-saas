import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Scan, Bug, FileText, FolderOpen, Crosshair,
  Shield, Bell, Settings, Wrench, Globe, LogOut,
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { cn } from '../../utils/cn'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/projects', icon: FolderOpen, label: 'Projects' },
  { to: '/targets', icon: Crosshair, label: 'Targets' },
  { to: '/scans', icon: Scan, label: 'Scans' },
  { to: '/findings', icon: Bug, label: 'Findings' },
  { to: '/reports', icon: FileText, label: 'Reports' },
  { to: '/tools', icon: Wrench, label: 'Tools' },
  { to: '/compliance', icon: Shield, label: 'Compliance' },
  { to: '/threat-intel', icon: Globe, label: 'Threat Intel' },
  { to: '/notifications', icon: Bell, label: 'Notifications' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  const { user, logout } = useAuthStore()

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-[var(--color-bg-secondary)] border-r border-[var(--color-border)] flex flex-col z-40">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-[var(--color-border)]">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Shield className="w-6 h-6 text-red-500" />
          Red Team SaaS
        </h1>
        <p className="text-xs text-[var(--color-text-secondary)] mt-1">Security Operations Platform</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm mb-1 transition-colors',
                isActive
                  ? 'bg-indigo-600/20 text-indigo-400 font-medium'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] hover:text-white',
              )
            }
          >
            <Icon className="w-4.5 h-4.5" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="border-t border-[var(--color-border)] p-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-sm font-medium text-white">
            {user?.full_name?.[0] || user?.username?.[0] || '?'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.full_name || user?.username}</p>
            <p className="text-xs text-[var(--color-text-secondary)] capitalize">{user?.role}</p>
          </div>
          <button onClick={logout} className="text-[var(--color-text-secondary)] hover:text-red-400 transition-colors">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}
