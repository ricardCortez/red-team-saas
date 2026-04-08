import { useState, useEffect } from 'react'
import { useAuthStore } from '../store/authStore'
import { authService } from '../services/authService'
import { aiService, type AIConfig, type AIProviderMeta } from '../services/aiService'
import Card from '../components/Common/Card'
import AIProviderCard from '../components/AI/AIProviderCard'

export default function SettingsPage() {
  const { user, setUser } = useAuthStore()
  const [activeTab, setActiveTab] = useState('profile')
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [profileMsg, setProfileMsg] = useState<{ text: string; ok: boolean } | null>(null)
  const [currentPwd, setCurrentPwd] = useState('')
  const [newPwd, setNewPwd] = useState('')
  const [pwdMsg, setPwdMsg] = useState<{ text: string; ok: boolean } | null>(null)
  const [saving, setSaving] = useState(false)
  const [providers, setProviders] = useState<AIProviderMeta[]>([])
  const [configs, setConfigs] = useState<AIConfig[]>([])

  const tabs = [
    { id: 'profile', label: 'Profile' },
    { id: 'security', label: 'Security' },
    { id: 'notifications', label: 'Notifications' },
    { id: 'ai', label: 'AI' },
    { id: 'api', label: 'API Keys' },
  ]

  useEffect(() => {
    if (activeTab === 'ai') {
      aiService.getProviders().then(setProviders).catch(() => {})
      aiService.getConfigs().then(setConfigs).catch(() => {})
    }
  }, [activeTab])

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setProfileMsg(null)
    try {
      const updated = await authService.updateProfile({ full_name: fullName })
      setUser(updated)
      setProfileMsg({ text: 'Profile updated.', ok: true })
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
      setPwdMsg({ text: 'Password updated.', ok: true })
    } catch (err: any) {
      setPwdMsg({ text: err?.response?.data?.detail || 'Failed to change password.', ok: false })
    } finally {
      setSaving(false)
    }
  }

  const upsertConfig = (cfg: AIConfig) => setConfigs((prev) => {
    const idx = prev.findIndex((c) => c.provider === cfg.provider)
    if (idx >= 0) { const next = [...prev]; next[idx] = cfg; return next }
    return [...prev, cfg]
  })

  const inputStyle = { background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }
  const inputClass = "w-full px-4 py-2 rounded-sm text-white focus:outline-none font-mono text-sm"

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-white font-mono tracking-wide">
        <span style={{ color: 'var(--neon-green)' }}>{'>'}</span> Settings
      </h2>

      <div className="flex gap-1 rounded-sm p-1 w-fit"
        style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}>
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className="px-4 py-2 rounded-sm text-sm font-mono transition-all"
            style={activeTab === t.id
              ? { background: 'rgba(0,255,65,0.1)', color: 'var(--neon-green)', border: '1px solid var(--neon-green)' }
              : { color: 'var(--color-text-secondary)', border: '1px solid transparent' }}>
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'profile' && (
        <Card title="Profile Information">
          <form onSubmit={handleSaveProfile} className="space-y-4 max-w-lg">
            <div>
              <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">Full Name</label>
              <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
                className={inputClass} style={inputStyle}
                onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'} />
            </div>
            <div>
              <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">Email</label>
              <input type="email" defaultValue={user?.email || ''} disabled
                className={inputClass + ' cursor-not-allowed opacity-50'} style={inputStyle} />
            </div>
            <div>
              <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">Role</label>
              <input type="text" defaultValue={user?.role || ''} disabled
                className={inputClass + ' cursor-not-allowed opacity-50'} style={inputStyle} />
            </div>
            {profileMsg && (
              <p className="text-xs font-mono" style={{ color: profileMsg.ok ? 'var(--neon-green)' : 'var(--neon-red)' }}>
                {profileMsg.ok ? '✓' : '✗'} {profileMsg.text}
              </p>
            )}
            <button type="submit" disabled={saving} className="px-4 py-2 rounded-sm text-sm font-mono btn-neon disabled:opacity-50">
              {saving ? 'saving...' : 'save changes'}
            </button>
          </form>
        </Card>
      )}

      {activeTab === 'security' && (
        <Card title="Change Password">
          <form onSubmit={handleChangePassword} className="space-y-4 max-w-lg">
            <div>
              <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">Current Password</label>
              <input type="password" value={currentPwd} onChange={(e) => setCurrentPwd(e.target.value)} required
                className={inputClass} style={inputStyle}
                onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'} />
            </div>
            <div>
              <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">New Password</label>
              <input type="password" value={newPwd} onChange={(e) => setNewPwd(e.target.value)} required minLength={8}
                className={inputClass} style={inputStyle}
                onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'} />
            </div>
            {pwdMsg && (
              <p className="text-xs font-mono" style={{ color: pwdMsg.ok ? 'var(--neon-green)' : 'var(--neon-red)' }}>
                {pwdMsg.ok ? '✓' : '✗'} {pwdMsg.text}
              </p>
            )}
            <button type="submit" disabled={saving} className="px-4 py-2 rounded-sm text-sm font-mono btn-neon disabled:opacity-50">
              {saving ? 'updating...' : 'update password'}
            </button>
          </form>
        </Card>
      )}

      {activeTab === 'notifications' && (
        <Card title="Notification Preferences">
          <div className="space-y-3 max-w-lg">
            {['Email alerts', 'Slack notifications', 'Webhook alerts', 'Critical findings only'].map((label) => (
              <label key={label} className="flex items-center justify-between py-2 border-b border-[var(--color-border)]">
                <span className="text-sm font-mono text-white">{label}</span>
                <input type="checkbox" defaultChecked className="w-4 h-4 accent-[var(--neon-green)]" />
              </label>
            ))}
          </div>
        </Card>
      )}

      {activeTab === 'ai' && (
        <div className="space-y-6">
          <div>
            <h3 className="text-sm font-mono font-semibold mb-3" style={{ color: 'var(--neon-green)' }}>
              // Local AI Providers
            </h3>
            <div className="space-y-2">
              {providers.filter((p) => p.type === 'local').map((meta) => (
                <AIProviderCard key={meta.provider} meta={meta}
                  config={configs.find((c) => c.provider === meta.provider)}
                  onSaved={upsertConfig} />
              ))}
            </div>
          </div>
          <div>
            <h3 className="text-sm font-mono font-semibold mb-3" style={{ color: 'var(--neon-blue)' }}>
              // Cloud AI Providers
            </h3>
            <div className="space-y-2">
              {providers.filter((p) => p.type === 'cloud').map((meta) => (
                <AIProviderCard key={meta.provider} meta={meta}
                  config={configs.find((c) => c.provider === meta.provider)}
                  onSaved={upsertConfig} />
              ))}
            </div>
          </div>
          <div>
            <h3 className="text-sm font-mono font-semibold mb-3" style={{ color: 'var(--neon-purple)' }}>
              // Custom Provider
            </h3>
            <div className="space-y-2">
              {providers.filter((p) => p.type === 'custom').map((meta) => (
                <AIProviderCard key={meta.provider} meta={meta}
                  config={configs.find((c) => c.provider === meta.provider)}
                  onSaved={upsertConfig} />
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'api' && (
        <Card title="API Keys">
          <p className="text-sm font-mono text-[var(--color-text-secondary)] mb-4">Manage API keys for programmatic access.</p>
          <button className="px-4 py-2 rounded-sm text-sm font-mono btn-neon">generate new key</button>
        </Card>
      )}
    </div>
  )
}
