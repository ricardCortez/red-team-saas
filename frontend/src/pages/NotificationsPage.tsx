import { Bell, CheckCheck, Trash2 } from 'lucide-react'
import { useNotificationStore } from '../store/notificationStore'
import Badge from '../components/Common/Badge'
import EmptyState from '../components/Common/EmptyState'
import { formatDate } from '../utils/cn'

export default function NotificationsPage() {
  const { notifications, markRead, markAllRead, clear } = useNotificationStore()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white">Notifications</h2>
        {notifications.length > 0 && (
          <div className="flex gap-2">
            <button onClick={markAllRead} className="px-3 py-2 bg-[var(--color-bg-tertiary)] text-white rounded-lg text-sm flex items-center gap-2">
              <CheckCheck className="w-4 h-4" /> Mark All Read
            </button>
            <button onClick={clear} className="px-3 py-2 bg-red-500/10 text-red-400 rounded-lg text-sm flex items-center gap-2">
              <Trash2 className="w-4 h-4" /> Clear All
            </button>
          </div>
        )}
      </div>

      {notifications.length === 0 ? (
        <EmptyState icon={<Bell className="w-12 h-12" />} title="No notifications" description="You're all caught up! Notifications from scans and alerts will appear here." />
      ) : (
        <div className="space-y-2">
          {notifications.map((n) => (
            <div key={n.id}
              className={`p-4 rounded-xl border transition-colors cursor-pointer ${n.read
                ? 'bg-[var(--color-bg-secondary)] border-[var(--color-border)]'
                : 'bg-[var(--color-bg-secondary)] border-indigo-500/30'}`}
              onClick={() => markRead(n.id)}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-white font-medium text-sm">{n.title}</h3>
                    <Badge text={n.severity} variant="severity" />
                    {!n.read && <span className="w-2 h-2 bg-indigo-500 rounded-full" />}
                  </div>
                  <p className="text-sm text-[var(--color-text-secondary)]">{n.message}</p>
                </div>
                <span className="text-xs text-[var(--color-text-secondary)] whitespace-nowrap ml-4">{formatDate(n.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
