import { useEffect, useState } from 'react'
import { Plus, Play, XCircle, RefreshCw, Wand2, Settings2, Brain, FileText, Trash2, Loader2 } from 'lucide-react'
import { scanService } from '../services/scanService'
import { toolService } from '../services/toolService'
import api from '../services/api'
import type { Scan, Tool, Project } from '../types'
import Card from '../components/Common/Card'
import Badge from '../components/Common/Badge'
import Loading from '../components/Common/Loading'
import EmptyState from '../components/Common/EmptyState'
import Modal from '../components/Common/Modal'
import { formatDate } from '../utils/cn'

type ExecutionMode = 'manual' | 'ia_assisted' | 'template'

const SCAN_TEMPLATES = [
  { name: 'Quick Recon', scan_type: 'recon', tools: ['nmap'], description: 'Fast port scan + service detection', options: { profile: 'quick' } },
  { name: 'Full Network Scan', scan_type: 'full', tools: ['nmap', 'nikto', 'gobuster'], description: 'Complete network enumeration', options: { profile: 'full' } },
  { name: 'Web Application Audit', scan_type: 'vuln_scan', tools: ['nikto', 'gobuster', 'wpscan', 'sqlmap'], description: 'Full web application security audit', options: {} },
  { name: 'Brute Force Attack', scan_type: 'brute_force', tools: ['hydra', 'medusa', 'john'], description: 'Credential testing suite', options: {} },
  { name: 'OSINT Gathering', scan_type: 'recon', tools: ['shodan', 'theharvester', 'whois', 'hunter_io'], description: 'Open source intelligence collection', options: {} },
  { name: 'Exploitation Chain', scan_type: 'exploitation', tools: ['sqlmap', 'metasploit'], description: 'Automated exploitation pipeline', options: {} },
  { name: 'Post-Exploitation', scan_type: 'post_exploit', tools: ['mimikatz', 'empire', 'lateral_movement'], description: 'Post-exploitation & lateral movement', options: {} },
]

export default function ScansPage() {
  const [scans, setScans] = useState<Scan[]>([])
  const [tools, setTools] = useState<Tool[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [actionLoading, setActionLoading] = useState<Record<number, string>>({})
  const [executionMode, setExecutionMode] = useState<ExecutionMode>('manual')
  const [form, setForm] = useState({
    name: '',
    scan_type: 'recon',
    target: '',
    tools: [] as string[],
    options: {} as Record<string, unknown>,
    project_id: 0,
  })
  const [iaPrompt, setIaPrompt] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState<number | null>(null)

  const load = () => {
    setLoading(true)
    scanService.list()
      .then(setScans)
      .catch(() => setScans([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    toolService.listAvailable().then(setTools).catch(() => {})
    api.get('/projects/').then((r) => {
      const items = Array.isArray(r.data) ? r.data : r.data.items ?? []
      setProjects(items)
      if (items.length > 0) setForm((f) => ({ ...f, project_id: items[0].id }))
    }).catch(() => {})
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setSubmitError('')

    let payload = { ...form }
    if (executionMode === 'template' && selectedTemplate !== null) {
      const tmpl = SCAN_TEMPLATES[selectedTemplate]
      payload = { ...payload, name: payload.name || tmpl.name, scan_type: tmpl.scan_type, tools: tmpl.tools, options: tmpl.options }
    } else if (executionMode === 'ia_assisted') {
      payload = { ...payload, name: payload.name || 'IA-Assisted Scan', options: { ...payload.options, ia_prompt: iaPrompt, ia_assisted: true } }
    }

    // Ensure name has a value (min 3 chars required by backend)
    if (!payload.name) payload.name = `Scan ${Date.now()}`
    if (payload.name.length < 3) payload.name = `Scan - ${payload.name}`

    // Guard against missing project
    if (!payload.project_id) {
      setSubmitError('Please select a project first')
      setSubmitting(false)
      return
    }

    try {
      await scanService.create(payload as unknown as Partial<Scan>)
      setShowCreate(false)
      resetForm()
      load()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setSubmitError(Array.isArray(detail) ? detail.map((d: any) => d.msg).join(', ') : detail || 'Failed to create scan')
    } finally {
      setSubmitting(false)
    }
  }

  const handleRun = async (id: number) => {
    setActionLoading((prev) => ({ ...prev, [id]: 'run' }))
    try {
      await scanService.run(id)
      load()
    } catch (err: any) {
      // If run endpoint fails (e.g. Celery not running), still refresh to show current state
      load()
    } finally {
      setActionLoading((prev) => { const n = { ...prev }; delete n[id]; return n })
    }
  }

  const handleCancel = async (id: number) => {
    setActionLoading((prev) => ({ ...prev, [id]: 'cancel' }))
    try {
      await scanService.cancel(id)
      load()
    } catch {
      load()
    } finally {
      setActionLoading((prev) => { const n = { ...prev }; delete n[id]; return n })
    }
  }

  const handleDelete = async (id: number) => {
    setActionLoading((prev) => ({ ...prev, [id]: 'delete' }))
    try {
      await scanService.delete(id)
      setScans((prev) => prev.filter((s) => s.id !== id))
    } catch {
      load()
    } finally {
      setActionLoading((prev) => { const n = { ...prev }; delete n[id]; return n })
    }
  }

  const resetForm = () => {
    setForm({ name: '', scan_type: 'recon', target: '', tools: [], options: {}, project_id: projects[0]?.id || 0 })
    setIaPrompt('')
    setSelectedTemplate(null)
    setExecutionMode('manual')
    setSubmitError('')
  }

  const toggleTool = (name: string) => {
    setForm((f) => ({
      ...f,
      tools: f.tools.includes(name) ? f.tools.filter((t) => t !== name) : [...f.tools, name],
    }))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">Scans</h2>
          <p className="text-sm text-[var(--color-text-secondary)]">{scans.length} scans total</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} disabled={loading} className="px-3 py-2 bg-[var(--color-bg-tertiary)] text-white rounded-lg hover:bg-[var(--color-bg-tertiary)]/80 text-sm flex items-center gap-2 disabled:opacity-50">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm flex items-center gap-2">
            <Plus className="w-4 h-4" /> New Scan
          </button>
        </div>
      </div>

      {/* Execution Modes Cards */}
      <div className="grid grid-cols-3 gap-4">
        {([
          { mode: 'manual' as const, label: 'Manual', icon: Settings2, color: 'indigo', desc: 'Full control over tool selection, parameters, and target configuration.' },
          { mode: 'ia_assisted' as const, label: 'IA-Assisted', icon: Brain, color: 'purple', desc: 'Describe your objective and let AI select the best tools and strategy.' },
          { mode: 'template' as const, label: 'Templates', icon: FileText, color: 'green', desc: 'Pre-configured scan profiles for common security testing scenarios.' },
        ]).map(({ mode, label, icon: Icon, color, desc }) => (
          <button
            key={mode}
            onClick={() => { setExecutionMode(mode); setShowCreate(true) }}
            className={`p-4 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl hover:border-${color}-500/50 transition-colors text-left group`}
          >
            <div className="flex items-center gap-3 mb-2">
              <div className={`p-2 bg-${color}-500/10 rounded-lg`}>
                <Icon className={`w-5 h-5 text-${color}-400`} />
              </div>
              <h3 className="text-white font-medium">{label}</h3>
            </div>
            <p className="text-xs text-[var(--color-text-secondary)]">{desc}</p>
          </button>
        ))}
      </div>

      {loading ? (
        <Loading text="Loading scans..." />
      ) : scans.length === 0 ? (
        <EmptyState title="No scans yet" description="Create your first scan using one of the execution modes above." />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[var(--color-text-secondary)] border-b border-[var(--color-border)]">
                  <th className="pb-3 font-medium">Name</th>
                  <th className="pb-3 font-medium">Type</th>
                  <th className="pb-3 font-medium">Target</th>
                  <th className="pb-3 font-medium">Tools</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Progress</th>
                  <th className="pb-3 font-medium">Created</th>
                  <th className="pb-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]">
                {scans.map((s) => {
                  const busy = actionLoading[s.id]
                  return (
                    <tr key={s.id} className="hover:bg-[var(--color-bg-tertiary)]/30">
                      <td className="py-3 text-white font-medium">{s.name || `Scan #${s.id}`}</td>
                      <td className="py-3 text-[var(--color-text-secondary)]">{s.scan_type}</td>
                      <td className="py-3 text-[var(--color-text-secondary)] font-mono text-xs">{s.target || '-'}</td>
                      <td className="py-3 text-[var(--color-text-secondary)] text-xs">{Array.isArray(s.tools) && s.tools.length > 0 ? s.tools.join(', ') : '-'}</td>
                      <td className="py-3"><Badge text={s.status} variant="status" /></td>
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-20 h-1.5 bg-[var(--color-bg-tertiary)] rounded-full">
                            <div className="h-1.5 bg-indigo-500 rounded-full" style={{ width: `${s.progress || 0}%` }} />
                          </div>
                          <span className="text-xs text-[var(--color-text-secondary)]">{s.progress || 0}%</span>
                        </div>
                      </td>
                      <td className="py-3 text-[var(--color-text-secondary)]">{formatDate(s.created_at)}</td>
                      <td className="py-3">
                        <div className="flex gap-1">
                          {busy ? (
                            <Loader2 className="w-4 h-4 animate-spin text-[var(--color-text-secondary)]" />
                          ) : (
                            <>
                              {(s.status === 'pending' || s.status === 'failed') && (
                                <button onClick={() => handleRun(s.id)} className="p-1.5 text-green-400 hover:bg-green-400/10 rounded" title="Run">
                                  <Play className="w-4 h-4" />
                                </button>
                              )}
                              {(s.status === 'running' || s.status === 'pending') && (
                                <button onClick={() => handleCancel(s.id)} className="p-1.5 text-yellow-400 hover:bg-yellow-400/10 rounded" title="Cancel">
                                  <XCircle className="w-4 h-4" />
                                </button>
                              )}
                              {(s.status === 'completed' || s.status === 'failed' || s.status === 'cancelled') && (
                                <button onClick={() => handleDelete(s.id)} className="p-1.5 text-red-400 hover:bg-red-400/10 rounded" title="Delete">
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Create Scan Modal */}
      <Modal open={showCreate} onClose={() => { if (!submitting) { setShowCreate(false); resetForm() } }} title="Create New Scan" size="lg">
        <div className="flex gap-1 mb-5 bg-[var(--color-bg-tertiary)] p-1 rounded-lg">
          {([
            { key: 'manual' as const, label: 'Manual', icon: Settings2 },
            { key: 'ia_assisted' as const, label: 'IA-Assisted', icon: Brain },
            { key: 'template' as const, label: 'Templates', icon: FileText },
          ]).map(({ key, label, icon: Icon }) => (
            <button key={key} type="button" onClick={() => setExecutionMode(key)}
              className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${executionMode === key ? 'bg-indigo-600 text-white' : 'text-[var(--color-text-secondary)] hover:text-white'}`}
            >
              <Icon className="w-4 h-4" /> {label}
            </button>
          ))}
        </div>

        <form onSubmit={handleCreate} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Scan Name</label>
              <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder={executionMode === 'template' ? 'Auto from template' : 'My scan'}
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
            </div>
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Project</label>
              <select value={form.project_id} onChange={(e) => setForm({ ...form, project_id: Number(e.target.value) })}
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none">
                {projects.length === 0 ? <option value={0}>No projects</option> : projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Target <span className="text-red-400">*</span></label>
            <input type="text" required value={form.target} onChange={(e) => setForm({ ...form, target: e.target.value })}
              placeholder="192.168.1.1 or example.com"
              className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
          </div>

          {executionMode === 'manual' && (
            <>
              <div>
                <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Scan Type</label>
                <select value={form.scan_type} onChange={(e) => setForm({ ...form, scan_type: e.target.value })}
                  className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none">
                  <option value="recon">Reconnaissance</option>
                  <option value="vuln_scan">Vulnerability Scan</option>
                  <option value="exploitation">Exploitation</option>
                  <option value="post_exploit">Post-Exploitation</option>
                  <option value="brute_force">Brute Force</option>
                  <option value="full">Full Scan</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-[var(--color-text-secondary)] mb-2">Select Tools ({form.tools.length} selected)</label>
                <div className="grid grid-cols-3 gap-2 max-h-48 overflow-y-auto pr-1">
                  {tools.map((t) => (
                    <button key={t.name} type="button" onClick={() => toggleTool(t.name)}
                      className={`px-3 py-2 rounded-lg text-xs text-left border transition-colors ${form.tools.includes(t.name) ? 'border-indigo-500 bg-indigo-500/10 text-indigo-300' : 'border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-text-secondary)]'}`}
                    >
                      <div className="flex items-center gap-1.5">
                        <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${t.available ? 'bg-green-400' : 'bg-gray-500'}`} />
                        <span className="font-medium truncate">{t.name}</span>
                      </div>
                      <span className="text-[10px] opacity-60">{t.category}</span>
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}

          {executionMode === 'ia_assisted' && (
            <>
              <div>
                <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Describe your objective</label>
                <textarea value={iaPrompt} onChange={(e) => setIaPrompt(e.target.value)} rows={4}
                  placeholder="e.g. Perform a full recon of the target, identify open ports and services, then check for common web vulnerabilities..."
                  className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50 resize-none" />
              </div>
              <div className="p-3 bg-purple-500/5 border border-purple-500/20 rounded-lg text-xs text-[var(--color-text-secondary)]">
                <Brain className="w-4 h-4 text-purple-400 inline mr-2" />
                AI will select tools, configure parameters, and chain execution automatically.
              </div>
            </>
          )}

          {executionMode === 'template' && (
            <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
              {SCAN_TEMPLATES.map((tmpl, idx) => (
                <button key={idx} type="button" onClick={() => { setSelectedTemplate(idx); setForm((f) => ({ ...f, scan_type: tmpl.scan_type, tools: tmpl.tools })) }}
                  className={`w-full p-3 rounded-lg border text-left transition-colors ${selectedTemplate === idx ? 'border-green-500 bg-green-500/10' : 'border-[var(--color-border)] hover:border-[var(--color-text-secondary)]'}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-white font-medium text-sm">{tmpl.name}</span>
                    <Badge text={tmpl.scan_type} variant="status" />
                  </div>
                  <p className="text-xs text-[var(--color-text-secondary)] mb-1">{tmpl.description}</p>
                  <div className="flex gap-1 flex-wrap">
                    {tmpl.tools.map((t) => <span key={t} className="px-1.5 py-0.5 bg-[var(--color-bg-tertiary)] rounded text-[10px] text-[var(--color-text-secondary)]">{t}</span>)}
                  </div>
                </button>
              ))}
            </div>
          )}

          {submitError && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">{submitError}</div>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t border-[var(--color-border)]">
            <button type="button" onClick={() => { setShowCreate(false); resetForm() }} disabled={submitting}
              className="px-4 py-2 text-[var(--color-text-secondary)] hover:text-white text-sm disabled:opacity-50">Cancel</button>
            <button type="submit"
              disabled={submitting || !form.target || (executionMode === 'template' && selectedTemplate === null)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-sm flex items-center gap-2"
            >
              {submitting ? <><Loader2 className="w-4 h-4 animate-spin" /> Creating...</> : <>{executionMode === 'ia_assisted' && <Wand2 className="w-4 h-4" />}Create Scan</>}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
