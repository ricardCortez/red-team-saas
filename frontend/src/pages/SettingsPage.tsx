import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import Card from '../components/Common/Card'

export default function SettingsPage() {
  const { user } = useAuthStore()
  const [activeTab, setActiveTab] = useState('profile')

  const tabs = [
    { id: 'profile', label: 'Profile' },
    { id: 'security', label: 'Security' },
    { id: 'notifications', label: 'Notifications' },
    { id: 'api', label: 'API Keys' },
  ]

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-white">Settings</h2>

      <div className="flex gap-1 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-1 w-fit">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className={`px-4 py-2 rounded-md text-sm transition-colors ${activeTab === t.id ? 'bg-indigo-600 text-white' : 'text-[var(--color-text-secondary)] hover:text-white'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'profile' && (
        <Card title="Profile Information">
          <div className="space-y-4 max-w-lg">
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Full Name</label>
              <input type="text" defaultValue={user?.full_name || ''}
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
            </div>
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Email</label>
              <input type="email" defaultValue={user?.email || ''} disabled
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-secondary)] cursor-not-allowed" />
            </div>
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Role</label>
              <input type="text" defaultValue={user?.role || ''} disabled
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-[var(--color-text-secondary)] capitalize cursor-not-allowed" />
            </div>
            <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm">Save Changes</button>
          </div>
        </Card>
      )}

      {activeTab === 'security' && (
        <Card title="Change Password">
          <div className="space-y-4 max-w-lg">
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Current Password</label>
              <input type="password" className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
            </div>
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">New Password</label>
              <input type="password" className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
            </div>
            <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm">Update Password</button>
          </div>
        </Card>
      )}

      {activeTab === 'notifications' && (
        <Card title="Notification Preferences">
          <div className="space-y-3 max-w-lg">
            {['Email alerts', 'Slack notifications', 'Webhook alerts', 'Critical findings only'].map((label) => (
              <label key={label} className="flex items-center justify-between py-2">
                <span className="text-sm text-white">{label}</span>
                <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-[var(--color-border)] bg-[var(--color-bg-tertiary)] text-indigo-600 focus:ring-indigo-500" />
              </label>
            ))}
          </div>
        </Card>
      )}

      {activeTab === 'api' && (
        <Card title="API Keys">
          <p className="text-sm text-[var(--color-text-secondary)] mb-4">Manage your API keys for programmatic access.</p>
          <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm">Generate New Key</button>
        </Card>
      )}
    </div>
  )
}
