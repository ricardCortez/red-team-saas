import { useEffect, useState } from 'react'
import { Plus, Play, XCircle, RefreshCw } from 'lucide-react'
import { scanService } from '../services/scanService'
import type { Scan } from '../types'
import Card from '../components/Common/Card'
import Badge from '../components/Common/Badge'
import Loading from '../components/Common/Loading'
import EmptyState from '../components/Common/EmptyState'
import Modal from '../components/Common/Modal'
import { formatDate } from '../utils/cn'

export default function ScansPage() {
  const [scans, setScans] = useState<Scan[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', scan_type: 'full', tool_name: 'nmap', target_id: 1, project_id: 1 })

  const load = () => {
    setLoading(true)
    scanService.list().then(setScans).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    await scanService.create(form as unknown as Partial<Scan>)
    setShowCreate(false)
    load()
  }

  if (loading) return <Loading text="Loading scans..." />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">Scans</h2>
          <p className="text-sm text-[var(--color-text-secondary)]">{scans.length} scans total</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="px-3 py-2 bg-[var(--color-bg-tertiary)] text-white rounded-lg hover:bg-[var(--color-bg-tertiary)]/80 text-sm flex items-center gap-2">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
          <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm flex items-center gap-2">
            <Plus className="w-4 h-4" /> New Scan
          </button>
        </div>
      </div>

      {scans.length === 0 ? (
        <EmptyState title="No scans yet" description="Create your first scan to start testing." action={
          <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm">Create Scan</button>
        } />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[var(--color-text-secondary)] border-b border-[var(--color-border)]">
                  <th className="pb-3 font-medium">Name</th>
                  <th className="pb-3 font-medium">Type</th>
                  <th className="pb-3 font-medium">Tool</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Progress</th>
                  <th className="pb-3 font-medium">Created</th>
                  <th className="pb-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]">
                {scans.map((s) => (
                  <tr key={s.id} className="hover:bg-[var(--color-bg-tertiary)]/30">
                    <td className="py-3 text-white font-medium">{s.name || `Scan #${s.id}`}</td>
                    <td className="py-3 text-[var(--color-text-secondary)]">{s.scan_type}</td>
                    <td className="py-3 text-[var(--color-text-secondary)]">{s.tool_name || '-'}</td>
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
                        {s.status === 'pending' && (
                          <button onClick={() => scanService.run(s.id).then(load)} className="p-1.5 text-green-400 hover:bg-green-400/10 rounded" title="Run">
                            <Play className="w-4 h-4" />
                          </button>
                        )}
                        {s.status === 'running' && (
                          <button onClick={() => scanService.cancel(s.id).then(load)} className="p-1.5 text-red-400 hover:bg-red-400/10 rounded" title="Cancel">
                            <XCircle className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create New Scan">
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Scan Name</label>
            <input type="text" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Scan Type</label>
              <select value={form.scan_type} onChange={(e) => setForm({ ...form, scan_type: e.target.value })}
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none">
                <option value="full">Full Scan</option>
                <option value="quick">Quick Scan</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Tool</label>
              <select value={form.tool_name} onChange={(e) => setForm({ ...form, tool_name: e.target.value })}
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none">
                <option value="nmap">Nmap</option>
                <option value="nikto">Nikto</option>
                <option value="gobuster">Gobuster</option>
                <option value="hydra">Hydra</option>
                <option value="wpscan">WPScan</option>
                <option value="sqlmap">SQLmap</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 text-[var(--color-text-secondary)] hover:text-white text-sm">Cancel</button>
            <button type="submit" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm">Create Scan</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
