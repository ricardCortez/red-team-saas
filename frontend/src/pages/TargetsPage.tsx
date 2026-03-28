import { useEffect, useState } from 'react'
import { Plus, Crosshair, Trash2 } from 'lucide-react'
import api from '../services/api'
import type { Target, Project } from '../types'
import Card from '../components/Common/Card'
import Badge from '../components/Common/Badge'
import Loading from '../components/Common/Loading'
import EmptyState from '../components/Common/EmptyState'
import Modal from '../components/Common/Modal'
import { formatDate } from '../utils/cn'

export default function TargetsPage() {
  const [targets, setTargets] = useState<Target[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [selectedProject, setSelectedProject] = useState<number>(0)
  const [form, setForm] = useState({ target_type: 'ip', value: '', description: '' })

  useEffect(() => {
    api.get('/projects/').then((r) => {
      const items = Array.isArray(r.data) ? r.data : r.data.items ?? []
      setProjects(items)
      if (items.length > 0) setSelectedProject(items[0].id)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selectedProject) { setLoading(false); return }
    loadTargets()
  }, [selectedProject])

  const loadTargets = () => {
    if (!selectedProject) return
    setLoading(true)
    api.get(`/projects/${selectedProject}/targets`)
      .then((r) => setTargets(Array.isArray(r.data) ? r.data : r.data.items ?? []))
      .catch(() => setTargets([]))
      .finally(() => setLoading(false))
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedProject) return
    await api.post(`/projects/${selectedProject}/targets`, form)
    setShowCreate(false)
    setForm({ target_type: 'ip', value: '', description: '' })
    loadTargets()
  }

  const handleDelete = async (targetId: number) => {
    if (!selectedProject) return
    await api.delete(`/projects/${selectedProject}/targets/${targetId}`)
    loadTargets()
  }

  if (loading) return <Loading text="Loading targets..." />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-semibold text-white">Targets</h2>
          {projects.length > 0 && (
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(Number(e.target.value))}
              className="px-3 py-1.5 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white text-sm"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          )}
        </div>
        <button
          onClick={() => setShowCreate(true)}
          disabled={!selectedProject}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-sm flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> Add Target
        </button>
      </div>

      {projects.length === 0 ? (
        <EmptyState icon={<Crosshair className="w-12 h-12" />} title="No projects" description="Create a project first to add targets." />
      ) : targets.length === 0 ? (
        <EmptyState icon={<Crosshair className="w-12 h-12" />} title="No targets" description="Add targets to scan." action={
          <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm">Add Target</button>
        } />
      ) : (
        <Card>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[var(--color-text-secondary)] border-b border-[var(--color-border)]">
                <th className="pb-3 font-medium">Type</th>
                <th className="pb-3 font-medium">Value</th>
                <th className="pb-3 font-medium">Description</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Created</th>
                <th className="pb-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {targets.map((t) => (
                <tr key={t.id} className="hover:bg-[var(--color-bg-tertiary)]/30">
                  <td className="py-3 text-[var(--color-text-secondary)] uppercase text-xs">{t.target_type}</td>
                  <td className="py-3 text-white font-mono text-xs">{t.value}</td>
                  <td className="py-3 text-[var(--color-text-secondary)]">{(t as any).description || '-'}</td>
                  <td className="py-3"><Badge text={t.status} variant="status" /></td>
                  <td className="py-3 text-[var(--color-text-secondary)]">{formatDate(t.created_at)}</td>
                  <td className="py-3">
                    <button onClick={() => handleDelete(t.id)} className="p-1.5 text-[var(--color-text-secondary)] hover:text-red-400 rounded"><Trash2 className="w-4 h-4" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Add Target">
        <form onSubmit={handleCreate} className="space-y-4">
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
          <div>
            <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Description (optional)</label>
            <input type="text" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              placeholder="Web server, DB host..." />
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
