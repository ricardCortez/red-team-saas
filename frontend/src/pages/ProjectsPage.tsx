import { useEffect, useState } from 'react'
import { Plus, FolderOpen, Trash2, Edit2 } from 'lucide-react'
import { projectService } from '../services/projectService'
import type { Project } from '../types'
import Card from '../components/Common/Card'
import Badge from '../components/Common/Badge'
import Loading from '../components/Common/Loading'
import EmptyState from '../components/Common/EmptyState'
import Modal from '../components/Common/Modal'
import { formatDate } from '../utils/cn'

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', description: '' })

  const load = () => {
    setLoading(true)
    projectService.list().then(setProjects).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    await projectService.create(form)
    setShowCreate(false)
    setForm({ name: '', description: '' })
    load()
  }

  const handleDelete = async (id: number) => {
    if (confirm('Delete this project?')) {
      await projectService.remove(id)
      load()
    }
  }

  if (loading) return <Loading text="Loading projects..." />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white">Projects</h2>
        <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm flex items-center gap-2">
          <Plus className="w-4 h-4" /> New Project
        </button>
      </div>

      {projects.length === 0 ? (
        <EmptyState icon={<FolderOpen className="w-12 h-12" />} title="No projects" description="Create your first project to organize your security assessments." action={
          <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm">Create Project</button>
        } />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => (
            <Card key={p.id}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="text-white font-semibold">{p.name}</h3>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-1">{p.description || 'No description'}</p>
                </div>
                <Badge text={p.status} variant="status" />
              </div>
              <p className="text-xs text-[var(--color-text-secondary)]">Created {formatDate(p.created_at)}</p>
              <div className="flex gap-2 mt-4 pt-3 border-t border-[var(--color-border)]">
                <button className="p-1.5 text-[var(--color-text-secondary)] hover:text-indigo-400 rounded"><Edit2 className="w-4 h-4" /></button>
                <button onClick={() => handleDelete(p.id)} className="p-1.5 text-[var(--color-text-secondary)] hover:text-red-400 rounded"><Trash2 className="w-4 h-4" /></button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Project">
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Project Name</label>
            <input type="text" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
          </div>
          <div>
            <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Description</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 h-24 resize-none" />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 text-[var(--color-text-secondary)] text-sm">Cancel</button>
            <button type="submit" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm">Create</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
