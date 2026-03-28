import { useEffect, useState } from 'react'
import { RefreshCw, Filter } from 'lucide-react'
import { findingsService } from '../services/findingsService'
import type { Finding, Severity } from '../types'
import Card from '../components/Common/Card'
import Badge from '../components/Common/Badge'
import Loading from '../components/Common/Loading'
import EmptyState from '../components/Common/EmptyState'
import { formatDate } from '../utils/cn'

const SEVERITIES: Severity[] = ['critical', 'high', 'medium', 'low', 'info']

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')

  const load = () => {
    setLoading(true)
    findingsService.list().then(setFindings).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const filtered = filter === 'all' ? findings : findings.filter((f) => f.severity === filter)

  if (loading) return <Loading text="Loading findings..." />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">Findings</h2>
          <p className="text-sm text-[var(--color-text-secondary)]">{findings.length} total findings</p>
        </div>
        <div className="flex gap-2">
          <div className="flex items-center gap-1 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-1">
            <button onClick={() => setFilter('all')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${filter === 'all' ? 'bg-indigo-600 text-white' : 'text-[var(--color-text-secondary)] hover:text-white'}`}>
              All
            </button>
            {SEVERITIES.map((s) => (
              <button key={s} onClick={() => setFilter(s)}
                className={`px-3 py-1.5 rounded text-xs font-medium capitalize transition-colors ${filter === s ? 'bg-indigo-600 text-white' : 'text-[var(--color-text-secondary)] hover:text-white'}`}>
                {s}
              </button>
            ))}
          </div>
          <button onClick={load} className="px-3 py-2 bg-[var(--color-bg-tertiary)] text-white rounded-lg text-sm flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-5 gap-3">
        {SEVERITIES.map((s) => {
          const count = findings.filter((f) => f.severity === s).length
          return (
            <div key={s} className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-3 text-center cursor-pointer hover:border-indigo-500/50" onClick={() => setFilter(s)}>
              <p className="text-2xl font-bold text-white">{count}</p>
              <p className="text-xs text-[var(--color-text-secondary)] capitalize">{s}</p>
            </div>
          )
        })}
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon={<Filter className="w-12 h-12" />} title="No findings" description={filter !== 'all' ? `No ${filter} findings found.` : 'No findings have been detected yet.'} />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[var(--color-text-secondary)] border-b border-[var(--color-border)]">
                  <th className="pb-3 font-medium">Title</th>
                  <th className="pb-3 font-medium">Severity</th>
                  <th className="pb-3 font-medium">CVE</th>
                  <th className="pb-3 font-medium">CVSS</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]">
                {filtered.map((f) => (
                  <tr key={f.id} className="hover:bg-[var(--color-bg-tertiary)]/30">
                    <td className="py-3">
                      <p className="text-white font-medium">{f.title}</p>
                      <p className="text-xs text-[var(--color-text-secondary)] line-clamp-1 mt-0.5">{f.description}</p>
                    </td>
                    <td className="py-3"><Badge text={f.severity} variant="severity" /></td>
                    <td className="py-3 text-[var(--color-text-secondary)] font-mono text-xs">{f.cve_id || '-'}</td>
                    <td className="py-3 text-white font-medium">{f.cvss_score?.toFixed(1) || '-'}</td>
                    <td className="py-3"><Badge text={f.status} variant="status" /></td>
                    <td className="py-3 text-[var(--color-text-secondary)]">{formatDate(f.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
