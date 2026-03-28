import { useEffect, useState } from 'react'
import { Plus, Crosshair, Trash2 } from 'lucide-react'
import api from '../services/api'
import type { Target } from '../types'
import Card from '../components/Common/Card'
import Badge from '../components/Common/Badge'
import Loading from '../components/Common/Loading'
import EmptyState from '../components/Common/EmptyState'
import Modal from '../components/Common/Modal'
import { formatDate } from '../utils/cn'

export default function TargetsPage() {
  const [targets, setTargets] = useState<Target[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', target_type: 'ip', value: '', project_id: 1 })

  const load = () => {
    setLoading(true)
    api.get('/targets/').then((r) => setTargets(Array.isArray(r.data) ? r.data : r.data.items ?? [])).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.post('/targets/', form)
    setShowCreate(false)
    setForm({ name: '', target_type: 'ip', value: '', project_id: 1 })
    load()
  }

  if (loading) return <Loading text="Loading targets..." />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white">Targets</h2>
        <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm flex items-center gap-2">
          <Plus className="w-4 h-4" /> Add Target
        </button>
      </div>

      {targets.length === 0 ? (
        <EmptyState icon={<Crosshair className="w-12 h-12" />} title="No targets" description="Add targets to scan." action={
          <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm">Add Target</button>
        } />
      ) : (
        <Card>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[var(--color-text-secondary)] border-b border-[var(--color-border)]">
                <th className="pb-3 font-medium">Name</th>
                <th className="pb-3 font-medium">Type</th>
                <th className="pb-3 font-medium">Value</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Created</th>
                <th className="pb-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {targets.map((t) => (
                <tr key={t.id} className="hover:bg-[var(--color-bg-tertiary)]/30">
                  <td className="py-3 text-white font-medium">{t.name}</td>
                  <td className="py-3 text-[var(--color-text-secondary)] uppercase text-xs">{t.target_type}</td>
                  <td className="py-3 text-[var(--color-text-secondary)] font-mono text-xs">{t.value}</td>
                  <td className="py-3"><Badge text={t.status} variant="status" /></td>
                  <td className="py-3 text-[var(--color-text-secondary)]">{formatDate(t.created_at)}</td>
                  <td className="py-3">
                    <button onClick={() => api.delete(`/targets/${t.id}`).then(load)} className="p-1.5 text-[var(--color-text-secondary)] hover:text-red-400 rounded"><Trash2 className="w-4 h-4" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Add Target">
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Name</label>
            <input type="text" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Type</label>
              <select value={form.target_type} onChange={(e) => setForm({ ...form, target_type: e.target.value })}
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white">
                <option value="ip">IP Address</option>
                <option value="domain">Domain</option>
                <option value="url">URL</option>
                <option value="cidr">CIDR Range</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Value</label>
              <input type="text" required value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })}
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                placeholder="192.168.1.1" />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 text-[var(--color-text-secondary)] text-sm">Cancel</button>
            <button type="submit" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm">Add Target</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
