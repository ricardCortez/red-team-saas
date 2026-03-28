import { useEffect, useState } from 'react'
import { FileText, Download, Plus } from 'lucide-react'
import { reportService } from '../services/reportService'
import type { Report } from '../types'
import Card from '../components/Common/Card'
import Badge from '../components/Common/Badge'
import Loading from '../components/Common/Loading'
import EmptyState from '../components/Common/EmptyState'
import Modal from '../components/Common/Modal'
import { formatDate } from '../utils/cn'

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const [showGenerate, setShowGenerate] = useState(false)
  const [form, setForm] = useState({ name: '', report_type: 'executive', format: 'pdf', project_id: 1 })

  const load = () => {
    setLoading(true)
    reportService.list().then(setReports).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    await reportService.generate(form)
    setShowGenerate(false)
    load()
  }

  const handleDownload = async (report: Report) => {
    const blob = await reportService.download(report.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${report.name}.${report.format}`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) return <Loading text="Loading reports..." />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white">Reports</h2>
        <button onClick={() => setShowGenerate(true)} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm flex items-center gap-2">
          <Plus className="w-4 h-4" /> Generate Report
        </button>
      </div>

      {reports.length === 0 ? (
        <EmptyState icon={<FileText className="w-12 h-12" />} title="No reports" description="Generate a report from your scan results." action={
          <button onClick={() => setShowGenerate(true)} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm">Generate Report</button>
        } />
      ) : (
        <Card>
          <div className="divide-y divide-[var(--color-border)]">
            {reports.map((r) => (
              <div key={r.id} className="flex items-center justify-between py-4">
                <div className="flex items-center gap-4">
                  <div className="p-2 bg-indigo-500/10 rounded-lg"><FileText className="w-5 h-5 text-indigo-400" /></div>
                  <div>
                    <p className="text-white font-medium">{r.name}</p>
                    <p className="text-xs text-[var(--color-text-secondary)]">{r.report_type} &middot; {r.format.toUpperCase()} &middot; {formatDate(r.created_at)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge text={r.status} variant="status" />
                  {r.status === 'completed' && (
                    <button onClick={() => handleDownload(r)} className="p-2 text-indigo-400 hover:bg-indigo-400/10 rounded-lg">
                      <Download className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Modal open={showGenerate} onClose={() => setShowGenerate(false)} title="Generate Report">
        <form onSubmit={handleGenerate} className="space-y-4">
          <div>
            <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Report Name</label>
            <input type="text" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Type</label>
              <select value={form.report_type} onChange={(e) => setForm({ ...form, report_type: e.target.value })}
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white">
                <option value="executive">Executive Summary</option>
                <option value="technical">Technical Report</option>
                <option value="compliance">Compliance Report</option>
                <option value="findings">Findings Report</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Format</label>
              <select value={form.format} onChange={(e) => setForm({ ...form, format: e.target.value })}
                className="w-full px-4 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg text-white">
                <option value="pdf">PDF</option>
                <option value="html">HTML</option>
                <option value="xlsx">Excel</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setShowGenerate(false)} className="px-4 py-2 text-[var(--color-text-secondary)] text-sm">Cancel</button>
            <button type="submit" className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm">Generate</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
