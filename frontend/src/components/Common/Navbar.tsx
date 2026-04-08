import { Bell, Search, Terminal } from 'lucide-react'
import { useState } from 'react'
import { useNotificationStore } from '../../store/notificationStore'

interface NavbarProps {
  title: string
}

export default function Navbar({ title }: NavbarProps) {
  const { unreadCount } = useNotificationStore()
  const [search, setSearch] = useState('')

  return (
    <header className="h-16 bg-[var(--color-bg-secondary)]/90 backdrop-blur-sm flex items-center justify-between px-6 sticky top-0 z-30"
      style={{ borderBottom: '1px solid var(--neon-green)', boxShadow: '0 1px 16px #00ff4111' }}>
      <div className="flex items-center gap-3">
        <Terminal className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--neon-green)' }} />
        <h2 className="text-lg font-semibold text-white font-mono tracking-wide">{title}</h2>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--neon-green)', opacity: 0.6 }} />
          <input
            type="text"
            placeholder="Search..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-2 bg-[var(--color-bg-tertiary)] rounded-sm text-sm text-white placeholder-[var(--color-text-secondary)] focus:outline-none w-56 font-mono"
            style={{ border: '1px solid var(--color-border)', transition: 'border-color 0.2s' }}
            onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
            onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'}
          />
        </div>

        <button className="relative p-2 text-[var(--color-text-secondary)] hover:text-[var(--neon-green)] transition-colors">
          <Bell className="w-5 h-5" />
          {unreadCount > 0 && (
            <span className="absolute top-1 right-1 w-4 h-4 text-[#0a0f1e] text-[10px] font-bold flex items-center justify-center rounded-full"
              style={{ background: 'var(--neon-red)', boxShadow: 'var(--glow-red)' }}>
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>
      </div>
    </header>
  )
}
