import { Bell, Search } from 'lucide-react'
import { useState } from 'react'
import { useNotificationStore } from '../../store/notificationStore'

interface NavbarProps {
  title: string
}

export default function Navbar({ title }: NavbarProps) {
  const { unreadCount } = useNotificationStore()
  const [search, setSearch] = useState('')

  return (
    <header className="h-16 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]/80 backdrop-blur-sm flex items-center justify-between px-6 sticky top-0 z-30">
      <h2 className="text-lg font-semibold text-white">{title}</h2>

      <div className="flex items-center gap-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-secondary)]" />
          <input
            type="text"
            placeholder="Search..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-sm text-white placeholder-[var(--color-text-secondary)] focus:outline-none focus:ring-2 focus:ring-indigo-500/50 w-64"
          />
        </div>

        {/* Notifications */}
        <button className="relative p-2 text-[var(--color-text-secondary)] hover:text-white transition-colors">
          <Bell className="w-5 h-5" />
          {unreadCount > 0 && (
            <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold flex items-center justify-center rounded-full">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>
      </div>
    </header>
  )
}
