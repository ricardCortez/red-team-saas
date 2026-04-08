import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Scan, Bug, FileText, FolderOpen, Crosshair,
  Shield, Bell, Settings, Wrench, Globe, LogOut, Mail,
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { cn } from '../../utils/cn'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/projects', icon: FolderOpen, label: 'Projects' },
  { to: '/targets', icon: Crosshair, label: 'Targets' },
  { to: '/scans', icon: Scan, label: 'Scans' },
  { to: '/phishing', icon: Mail, label: 'Phishing' },
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
    <aside className="fixed left-0 top-0 h-screen w-64 bg-[var(--color-bg-secondary)] flex flex-col z-40"
      style={{ borderRight: '1px solid var(--neon-green)', boxShadow: '2px 0 16px #00ff4111' }}>
      {/* Logo */}
      <div className="px-6 py-5 border-b border-[var(--color-border)]">
        <h1 className="text-xl font-bold text-white flex items-center gap-2 font-mono">
          <Shield className="w-6 h-6" style={{ color: 'var(--neon-red)', filter: 'drop-shadow(0 0 6px var(--neon-red))' }} />
          <span style={{ color: 'var(--neon-green)', textShadow: 'var(--glow-green)' }}>RED</span>
          <span className="text-white">TEAM</span>
        </h1>
        <p className="text-xs mt-1 font-mono" style={{ color: 'var(--neon-green)', opacity: 0.6 }}>// Security Operations</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm mb-1 transition-all duration-200 font-mono',
                isActive
                  ? 'text-[var(--neon-green)] font-medium'
                  : 'text-[var(--color-text-secondary)] hover:text-white hover:bg-[var(--color-bg-tertiary)]',
              )
            }
            style={({ isActive }) => isActive ? {
              background: 'rgba(0,255,65,0.07)',
              borderLeft: '2px solid var(--neon-green)',
              boxShadow: 'inset 0 0 12px rgba(0,255,65,0.05)',
            } : { borderLeft: '2px solid transparent' }}
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="border-t border-[var(--color-border)] p-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-sm flex items-center justify-center text-sm font-bold font-mono"
            style={{ background: 'rgba(0,255,65,0.1)', border: '1px solid var(--neon-green)', color: 'var(--neon-green)' }}>
            {(user?.full_name?.[0] || user?.username?.[0] || '?').toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate font-mono">{user?.full_name || user?.username}</p>
            <p className="text-xs capitalize font-mono" style={{ color: 'var(--neon-green)', opacity: 0.7 }}>{user?.role}</p>
          </div>
          <button onClick={logout} className="text-[var(--color-text-secondary)] hover:text-[var(--neon-red)] transition-colors">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}
