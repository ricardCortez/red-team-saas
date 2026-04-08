import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { authService } from '../services/authService'
import Card from '../components/Common/Card'

export default function SettingsPage() {
  const { user, setUser } = useAuthStore()
  const [activeTab, setActiveTab] = useState('profile')
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [profileMsg, setProfileMsg] = useState<{ text: string; ok: boolean } | null>(null)
  const [currentPwd, setCurrentPwd] = useState('')
  const [newPwd, setNewPwd] = useState('')
  const [pwdMsg, setPwdMsg] = useState<{ text: string; ok: boolean } | null>(null)
  const [saving, setSaving] = useState(false)

  const tabs = [
    { id: 'profile', label: 'Profile' },
    { id: 'security', label: 'Security' },
    { id: 'notifications', label: 'Notifications' },
    { id: 'api', label: 'API Keys' },
  ]

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setProfileMsg(null)
    try {
      const updated = await authService.updateProfile({ full_name: fullName })
      setUser(updated)
      setProfileMsg({ text: 'Profile updated successfully.', ok: true })
    } catch {
      setProfileMsg({ text: 'Failed to update profile.', ok: false })
    } finally {
      setSaving(false)
    }
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentPwd || !newPwd) return
    setSaving(true)
    setPwdMsg(null)
    try {
      await authService.changePassword(currentPwd, newPwd)
      setCurrentPwd('')
      setNewPwd('')
      setPwdMsg({ text: 'Password updated successfully.', ok: true })
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setPwdMsg({ text: detail || 'Failed to change password.', ok: false })
    } finally {
      setSaving(false)
    }
  }

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
          <form onSubmit={handleSaveProfile} className="space-y-4 max-w-lg">
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Full Name</label>
              <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
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
            {profileMsg && (
              <p className={`text-sm ${profileMsg.ok ? 'text-green-400' : 'text-red-400'}`}>{profileMsg.text}</p>
            )}
            <button type="submit" disabled={saving}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </form>
        </Card>
      )}

      {activeTab === 'security' && (
        <Card title="Change Password">
          <form onSubmit={handleChangePassword} className="space-y-4 max-w-lg">
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Current Password</label>
              <input type="password" value={currentPwd} onChange={(e) => setCurrentPwd(e.target.value)} required
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
            </div>
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">New Password</label>
              <input type="password" value={newPwd} onChange={(e) => setNewPwd(e.target.value)} required minLength={8}
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
            </div>
            {pwdMsg && (
              <p className={`text-sm ${pwdMsg.ok ? 'text-green-400' : 'text-red-400'}`}>{pwdMsg.text}</p>
            )}
            <button type="submit" disabled={saving}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm disabled:opacity-50">
              {saving ? 'Updating...' : 'Update Password'}
            </button>
          </form>
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
