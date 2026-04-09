import { useEffect, useState } from 'react'
import {
  Mail, Plus, Play, Square, RefreshCw, Trash2,
  Loader2,
} from 'lucide-react'
import {
  phishingService,
  type PhishingCampaign,
  type PhishingTarget,
  type PhishingTargetResult,
} from '../services/phishingService'
import api from '../services/api'
import type { Project } from '../types'
import Card from '../components/Common/Card'
import Loading from '../components/Common/Loading'
import EmptyState from '../components/Common/EmptyState'
import Modal from '../components/Common/Modal'
import { formatDate } from '../utils/cn'

type DetailTab = 'targets' | 'results'

const STATUS_COLORS: Record<string, string> = {
  draft: 'text-gray-400',
  active: 'text-green-400',
  completed: 'text-blue-400',
  cancelled: 'text-red-400',
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="p-3 bg-[var(--color-bg-tertiary)] rounded-lg text-center">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-[var(--color-text-secondary)] mt-1">{label}</div>
    </div>
  )
}

function ClickRate({ sent, clicked }: { sent: number; clicked: number }) {
  const rate = sent > 0 ? Math.round((clicked / sent) * 100) : 0
  const color = rate > 30 ? 'bg-red-500' : rate > 10 ? 'bg-yellow-500' : 'bg-green-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
        <div className={`h-2 ${color} rounded-full transition-all`} style={{ width: `${Math.min(rate, 100)}%` }} />
      </div>
      <span className="text-xs text-[var(--color-text-secondary)] w-10 text-right">{rate}%</span>
    </div>
  )
}

export default function PhishingPage() {
  const [campaigns, setCampaigns] = useState<PhishingCampaign[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<Record<number, string>>({})

  const [showCreate, setShowCreate] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  const defaultCreateForm = () => ({
    project_id: 0,
    name: '',
    description: '',
    gophish_url: 'https://gophish:3333',
    gophish_api_key: localStorage.getItem('gophish_api_key') ?? '',
    template_name: 'Microsoft 365 - Account Verification',
    landing_page_name: 'Microsoft Login Page',
    smtp_profile_name: 'Test SMTP',
    target_group_name: 'Test Group',
    phishing_url: 'http://localhost:8080',
  })

  const [createForm, setCreateForm] = useState(defaultCreateForm)

  const [selectedCampaign, setSelectedCampaign] = useState<PhishingCampaign | null>(null)
  const [detailTab, setDetailTab] = useState<DetailTab>('targets')
  const [targets, setTargets] = useState<PhishingTarget[]>([])
  const [results, setResults] = useState<PhishingTargetResult[]>([])
  const [loadingDetail, setLoadingDetail] = useState(false)

  const [showAddTargets, setShowAddTargets] = useState(false)
  const [targetsText, setTargetsText] = useState('')

  const load = () => {
    setLoading(true)
    phishingService.list()
      .then((r) => setCampaigns(r.items))
      .catch(() => setCampaigns([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    api.get('/projects/').then((r) => {
      const items: Project[] = Array.isArray(r.data) ? r.data : r.data.items ?? []
      setProjects(items)
      if (items.length > 0) setCreateForm((f) => ({ ...f, project_id: items[0].id }))
    }).catch(() => {})

    // Load GoPhish config from backend (falls back to localStorage, then empty)
    api.get('/phishing/campaigns/config').then((r) => {
      const cfg = r.data
      setCreateForm((f) => ({
        ...f,
        gophish_url: cfg.gophish_url || f.gophish_url,
        gophish_api_key: cfg.gophish_api_key || localStorage.getItem('gophish_api_key') || f.gophish_api_key,
        phishing_url: cfg.phishing_url || f.phishing_url,
      }))
      if (cfg.gophish_api_key) localStorage.setItem('gophish_api_key', cfg.gophish_api_key)
    }).catch(() => {
      // Fall back to localStorage only
      const savedKey = localStorage.getItem('gophish_api_key')
      if (savedKey) setCreateForm((f) => ({ ...f, gophish_api_key: savedKey }))
    })
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!createForm.project_id) { setSubmitError('Select a project'); return }
    setSubmitting(true)
    setSubmitError('')
    try {
      // Persist API key for next time
      if (createForm.gophish_api_key) {
        localStorage.setItem('gophish_api_key', createForm.gophish_api_key)
      }
      await phishingService.create(createForm as unknown as Record<string, unknown>)
      setShowCreate(false)
      resetCreateForm()
      load()
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } } }
      const detail = e?.response?.data?.detail
      setSubmitError(Array.isArray(detail) ? (detail as { msg: string }[]).map((d) => d.msg).join(', ') : String(detail || 'Failed to create campaign'))
    } finally {
      setSubmitting(false)
    }
  }

  const resetCreateForm = () => {
    setCreateForm({ ...defaultCreateForm(), project_id: projects[0]?.id || 0 })
    setSubmitError('')
  }

  const handleLaunch = async (id: number) => {
    setActionLoading((p) => ({ ...p, [id]: 'launch' }))
    try {
      const updated = await phishingService.launch(id)
      setCampaigns((p) => p.map((c) => c.id === id ? updated : c))
      if (selectedCampaign?.id === id) setSelectedCampaign(updated)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e?.response?.data?.detail || 'Launch failed')
    } finally {
      setActionLoading((p) => { const n = { ...p }; delete n[id]; return n })
    }
  }

  const handleStop = async (id: number) => {
    setActionLoading((p) => ({ ...p, [id]: 'stop' }))
    try {
      const updated = await phishingService.stop(id)
      setCampaigns((p) => p.map((c) => c.id === id ? updated : c))
      if (selectedCampaign?.id === id) setSelectedCampaign(updated)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e?.response?.data?.detail || 'Stop failed')
    } finally {
      setActionLoading((p) => { const n = { ...p }; delete n[id]; return n })
    }
  }

  const handleSync = async (id: number) => {
    setActionLoading((p) => ({ ...p, [id]: 'sync' }))
    try {
      const updated = await phishingService.syncStats(id)
      setCampaigns((p) => p.map((c) => c.id === id ? updated : c))
      if (selectedCampaign?.id === id) setSelectedCampaign(updated)
    } finally {
      setActionLoading((p) => { const n = { ...p }; delete n[id]; return n })
    }
  }

  const handleDelete = async (id: number) => {
    setActionLoading((p) => ({ ...p, [id]: 'delete' }))
    try {
      await phishingService.delete(id)
      setCampaigns((p) => p.filter((c) => c.id !== id))
      if (selectedCampaign?.id === id) setSelectedCampaign(null)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e?.response?.data?.detail || 'Delete failed')
    } finally {
      setActionLoading((p) => { const n = { ...p }; delete n[id]; return n })
    }
  }

  const openDetail = async (campaign: PhishingCampaign) => {
    setSelectedCampaign(campaign)
    setDetailTab('targets')
    setLoadingDetail(true)
    try {
      const t = await phishingService.listTargets(campaign.id)
      setTargets(t)
    } finally {
      setLoadingDetail(false)
    }
  }

  const loadResults = async (campaign: PhishingCampaign) => {
    setLoadingDetail(true)
    try {
      const r = await phishingService.getResults(campaign.id)
      setResults(r.results)
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleAddTargets = async () => {
    if (!selectedCampaign) return
    const lines = targetsText.split('\n').map((l) => l.trim()).filter(Boolean)
    const parsed = lines.map((line) => {
      const parts = line.split(',').map((p) => p.trim())
      return {
        email: parts[0] || '',
        first_name: parts[1] || undefined,
        last_name: parts[2] || undefined,
        position: parts[3] || undefined,
      }
    }).filter((t) => t.email)

    if (!parsed.length) return
    try {
      const added = await phishingService.addTargets(selectedCampaign.id, parsed)
      setTargets((prev) => [...prev, ...added])
      setTargetsText('')
      setShowAddTargets(false)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      alert(e?.response?.data?.detail || 'Failed to add targets')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <Mail className="w-5 h-5 text-red-400" /> Phishing Campaigns
          </h2>
          <p className="text-sm text-[var(--color-text-secondary)]">{campaigns.length} campaigns</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} disabled={loading} className="px-3 py-2 bg-[var(--color-bg-tertiary)] text-white rounded-lg hover:bg-[var(--color-bg-tertiary)]/80 text-sm flex items-center gap-2 disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm flex items-center gap-2">
            <Plus className="w-4 h-4" /> New Campaign
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Campaign list */}
        <div className="space-y-3">
          {loading ? <Loading text="Loading campaigns..." /> : campaigns.length === 0 ? (
            <EmptyState
              icon={<Mail className="w-12 h-12" />}
              title="No phishing campaigns"
              description="Create a campaign to simulate phishing attacks and measure employee security awareness."
              action={<button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm">New Campaign</button>}
            />
          ) : campaigns.map((c) => {
            const busy = actionLoading[c.id]
            const isSelected = selectedCampaign?.id === c.id
            return (
              <Card key={c.id} className={`cursor-pointer transition-colors ${isSelected ? 'border-red-500/50' : ''}`}>
                <div onClick={() => openDetail(c)} className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-white font-medium">{c.name}</h3>
                      {c.description && <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">{c.description}</p>}
                    </div>
                    <span className={`text-xs font-medium capitalize ${STATUS_COLORS[c.status] || 'text-gray-400'}`}>{c.status}</span>
                  </div>

                  {(c.status === 'active' || c.status === 'completed') && (
                    <div className="grid grid-cols-4 gap-2">
                      <StatCard label="Sent" value={c.stats_sent} color="text-blue-400" />
                      <StatCard label="Opened" value={c.stats_opened} color="text-yellow-400" />
                      <StatCard label="Clicked" value={c.stats_clicked} color="text-orange-400" />
                      <StatCard label="Submitted" value={c.stats_submitted} color="text-red-400" />
                    </div>
                  )}

                  {c.stats_sent > 0 && (
                    <div>
                      <p className="text-xs text-[var(--color-text-secondary)] mb-1">Click rate</p>
                      <ClickRate sent={c.stats_sent} clicked={c.stats_clicked} />
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between mt-3 pt-3 border-t border-[var(--color-border)]">
                  <span className="text-xs text-[var(--color-text-secondary)]">{formatDate(c.created_at)}</span>
                  <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                    {busy ? (
                      <Loader2 className="w-4 h-4 animate-spin text-[var(--color-text-secondary)]" />
                    ) : (
                      <>
                        {c.status === 'draft' && (
                          <button onClick={() => handleLaunch(c.id)} className="p-1.5 text-green-400 hover:bg-green-400/10 rounded" title="Launch">
                            <Play className="w-4 h-4" />
                          </button>
                        )}
                        {c.status === 'active' && (
                          <>
                            <button onClick={() => handleSync(c.id)} className="p-1.5 text-blue-400 hover:bg-blue-400/10 rounded" title="Sync stats">
                              <RefreshCw className="w-4 h-4" />
                            </button>
                            <button onClick={() => handleStop(c.id)} className="p-1.5 text-yellow-400 hover:bg-yellow-400/10 rounded" title="Stop">
                              <Square className="w-4 h-4" />
                            </button>
                          </>
                        )}
                        {(c.status === 'completed' || c.status === 'cancelled' || c.status === 'draft') && (
                          <button onClick={() => handleDelete(c.id)} className="p-1.5 text-red-400 hover:bg-red-400/10 rounded" title="Delete">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        {/* Detail panel */}
        {selectedCampaign && (
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-semibold">{selectedCampaign.name}</h3>
              <div className="flex gap-1">
                {(['targets', 'results'] as DetailTab[]).map((t) => (
                  <button key={t} onClick={() => {
                    setDetailTab(t)
                    if (t === 'results') loadResults(selectedCampaign)
                  }}
                    className={`px-3 py-1.5 rounded-lg text-xs capitalize transition-colors ${detailTab === t ? 'bg-red-600 text-white' : 'text-[var(--color-text-secondary)] hover:text-white'}`}
                  >{t}</button>
                ))}
              </div>
            </div>

            {loadingDetail ? <Loading text="Loading..." /> : (
              <>
                {detailTab === 'targets' && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm text-[var(--color-text-secondary)]">{targets.length} targets</span>
                      {selectedCampaign.status === 'draft' && (
                        <button onClick={() => setShowAddTargets(true)} className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs flex items-center gap-1">
                          <Plus className="w-3 h-3" /> Add Targets
                        </button>
                      )}
                    </div>
                    {targets.length === 0 ? (
                      <p className="text-sm text-[var(--color-text-secondary)] text-center py-8">No targets yet. Add targets to launch the campaign.</p>
                    ) : (
                      <div className="divide-y divide-[var(--color-border)] max-h-80 overflow-y-auto">
                        {targets.map((t) => (
                          <div key={t.id} className="py-2.5 flex items-center justify-between">
                            <div>
                              <p className="text-sm text-white">
                                {[t.first_name, t.last_name].filter(Boolean).join(' ')}
                                {' '}
                                <span className="text-[var(--color-text-secondary)]">{t.email}</span>
                              </p>
                              {t.position && <p className="text-xs text-[var(--color-text-secondary)]">{t.position}</p>}
                            </div>
                            <span className={`text-xs capitalize px-2 py-0.5 rounded-full ${
                              t.status === 'submitted_data' ? 'bg-red-500/20 text-red-400' :
                              t.status === 'clicked' ? 'bg-orange-500/20 text-orange-400' :
                              t.status === 'opened' ? 'bg-yellow-500/20 text-yellow-400' :
                              t.status === 'sent' ? 'bg-blue-500/20 text-blue-400' :
                              'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'
                            }`}>{t.status.replace('_', ' ')}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {detailTab === 'results' && (
                  <div>
                    {results.length === 0 ? (
                      <p className="text-sm text-[var(--color-text-secondary)] text-center py-8">No results yet. Launch the campaign first.</p>
                    ) : (
                      <div className="divide-y divide-[var(--color-border)] max-h-80 overflow-y-auto">
                        {results.map((r, i) => (
                          <div key={i} className="py-2.5 flex items-center justify-between">
                            <div>
                              <p className="text-sm text-white">{r.email}</p>
                              {r.ip && <p className="text-xs text-[var(--color-text-secondary)] font-mono">{r.ip}</p>}
                            </div>
                            <span className="text-xs text-[var(--color-text-secondary)]">{r.status}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </Card>
        )}
      </div>

      {/* Create Campaign Modal */}
      <Modal open={showCreate} onClose={() => { if (!submitting) { setShowCreate(false); resetCreateForm() } }} title="New Phishing Campaign" size="lg">
        <form onSubmit={handleCreate} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Campaign Name</label>
              <input required value={createForm.name} onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                placeholder="Q1 Phishing Test"
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-red-500/50" />
            </div>
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Project</label>
              <select value={createForm.project_id} onChange={(e) => setCreateForm({ ...createForm, project_id: Number(e.target.value) })}
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none">
                {projects.length === 0 ? <option value={0}>No projects</option> : projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Description</label>
            <input value={createForm.description} onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
              placeholder="Optional description"
              className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none" />
          </div>

          <div className="p-3 bg-[var(--color-bg-tertiary)] rounded-lg border border-[var(--color-border)] space-y-3">
            <p className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wide">GoPhish Server</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-[var(--color-text-secondary)] mb-1">GoPhish URL</label>
                <input required value={createForm.gophish_url} onChange={(e) => setCreateForm({ ...createForm, gophish_url: e.target.value })}
                  placeholder="https://gophish:3333"
                  className="w-full px-3 py-2 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-red-500/50" />
              </div>
              <div>
                <label className="block text-xs text-[var(--color-text-secondary)] mb-1">
                  API Key
                  {localStorage.getItem('gophish_api_key') && (
                    <span className="ml-2 text-green-400 text-xs">(auto-cargada)</span>
                  )}
                </label>
                <input required type="password" value={createForm.gophish_api_key} onChange={(e) => setCreateForm({ ...createForm, gophish_api_key: e.target.value })}
                  placeholder="GoPhish API key"
                  className="w-full px-3 py-2 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-red-500/50" />
              </div>
            </div>
          </div>

          <div className="p-3 bg-[var(--color-bg-tertiary)] rounded-lg border border-[var(--color-border)] space-y-3">
            <p className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wide">Campaign Resources (GoPhish names)</p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { key: 'template_name', label: 'Email Template' },
                { key: 'landing_page_name', label: 'Landing Page' },
                { key: 'smtp_profile_name', label: 'SMTP Profile' },
                { key: 'target_group_name', label: 'Target Group' },
              ].map(({ key, label }) => (
                <div key={key}>
                  <label className="block text-xs text-[var(--color-text-secondary)] mb-1">{label}</label>
                  <input value={(createForm as Record<string, string>)[key]} onChange={(e) => setCreateForm({ ...createForm, [key]: e.target.value })}
                    placeholder={`GoPhish ${label} name`}
                    className="w-full px-3 py-2 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg text-white text-sm focus:outline-none" />
                </div>
              ))}
            </div>
            <div>
              <label className="block text-xs text-[var(--color-text-secondary)] mb-1">Phishing URL</label>
              <input value={createForm.phishing_url} onChange={(e) => setCreateForm({ ...createForm, phishing_url: e.target.value })}
                placeholder="https://phishing.example.com"
                className="w-full px-3 py-2 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg text-white text-sm focus:outline-none" />
            </div>
          </div>

          {submitError && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">{submitError}</div>
          )}

          <div className="flex justify-end gap-3 pt-2 border-t border-[var(--color-border)]">
            <button type="button" onClick={() => { setShowCreate(false); resetCreateForm() }} disabled={submitting}
              className="px-4 py-2 text-[var(--color-text-secondary)] hover:text-white text-sm disabled:opacity-50">Cancel</button>
            <button type="submit" disabled={submitting || !createForm.project_id}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-lg text-sm flex items-center gap-2">
              {submitting ? <><Loader2 className="w-4 h-4 animate-spin" /> Creating...</> : 'Create Campaign'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Add Targets Modal */}
      <Modal open={showAddTargets} onClose={() => setShowAddTargets(false)} title="Add Targets">
        <div className="space-y-3">
          <p className="text-sm text-[var(--color-text-secondary)]">
            One target per line. Format: <code className="text-xs bg-[var(--color-bg-tertiary)] px-1 rounded">email, first_name, last_name, position</code>
          </p>
          <textarea value={targetsText} onChange={(e) => setTargetsText(e.target.value)} rows={8}
            placeholder={"john.doe@company.com, John, Doe, Engineer\njane.smith@company.com, Jane, Smith, Manager"}
            className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white text-sm font-mono focus:outline-none focus:ring-2 focus:ring-red-500/50 resize-none" />
          <div className="flex justify-end gap-3">
            <button onClick={() => setShowAddTargets(false)} className="px-4 py-2 text-[var(--color-text-secondary)] text-sm">Cancel</button>
            <button onClick={handleAddTargets} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm">
              Add Targets
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
