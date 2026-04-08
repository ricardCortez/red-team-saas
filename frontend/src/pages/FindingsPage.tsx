import { useEffect, useState } from 'react'
import { RefreshCw, Filter, Bot } from 'lucide-react'
import { findingsService } from '../services/findingsService'
import type { Finding, Severity } from '../types'
import Card from '../components/Common/Card'
import Badge from '../components/Common/Badge'
import Loading from '../components/Common/Loading'
import EmptyState from '../components/Common/EmptyState'
import AIAnalysisModal from '../components/AI/AIAnalysisModal'
import { formatDate } from '../utils/cn'

const SEVERITIES: Severity[] = ['critical', 'high', 'medium', 'low', 'info']

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')
  const [analyzingId, setAnalyzingId] = useState<number | null>(null)
  const [analyzingTitle, setAnalyzingTitle] = useState('')

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
          <h2 className="text-xl font-bold text-white font-mono">
            <span style={{ color: 'var(--neon-red)' }}>{'>'}</span> Findings
          </h2>
          <p className="text-sm font-mono text-[var(--color-text-secondary)]">{findings.length} total findings</p>
        </div>
        <div className="flex gap-2">
          <div className="flex items-center gap-1 rounded-sm p-1"
            style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}>
            <button onClick={() => setFilter('all')}
              className="px-3 py-1.5 rounded-sm text-xs font-mono transition-all"
              style={filter === 'all'
                ? { background: 'rgba(0,255,65,0.1)', color: 'var(--neon-green)', border: '1px solid var(--neon-green)' }
                : { color: 'var(--color-text-secondary)', border: '1px solid transparent' }}>
              all
            </button>
            {SEVERITIES.map((s) => (
              <button key={s} onClick={() => setFilter(s)}
                className="px-3 py-1.5 rounded-sm text-xs font-mono capitalize transition-all"
                style={filter === s
                  ? { background: 'rgba(0,255,65,0.1)', color: 'var(--neon-green)', border: '1px solid var(--neon-green)' }
                  : { color: 'var(--color-text-secondary)', border: '1px solid transparent' }}>
                {s}
              </button>
            ))}
          </div>
          <button onClick={load} className="px-3 py-2 rounded-sm text-white flex items-center gap-2 transition-colors"
            style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }}>
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-5 gap-3">
        {SEVERITIES.map((s) => {
          const count = findings.filter((f) => f.severity === s).length
          const colors: Record<string, string> = {
            critical: 'var(--neon-red)', high: '#ff6b00', medium: '#ffd000',
            low: 'var(--neon-blue)', info: 'var(--color-text-secondary)',
          }
          return (
            <div key={s} className="rounded-sm p-3 text-center cursor-pointer transition-all"
              onClick={() => setFilter(s)}
              style={{ background: 'var(--color-bg-secondary)', border: `1px solid ${filter === s ? colors[s] : 'var(--color-border)'}` }}>
              <p className="text-2xl font-bold font-mono" style={{ color: colors[s] }}>{count}</p>
              <p className="text-xs font-mono capitalize text-[var(--color-text-secondary)]">{s}</p>
            </div>
          )
        })}
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon={<Filter className="w-12 h-12" />} title="No findings"
          description={filter !== 'all' ? `No ${filter} findings found.` : 'No findings detected yet.'} />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[var(--color-text-secondary)] border-b border-[var(--color-border)]">
                  <th className="pb-3 font-mono text-xs">Title</th>
                  <th className="pb-3 font-mono text-xs">Severity</th>
                  <th className="pb-3 font-mono text-xs">Host</th>
                  <th className="pb-3 font-mono text-xs">Risk</th>
                  <th className="pb-3 font-mono text-xs">Status</th>
                  <th className="pb-3 font-mono text-xs">Date</th>
                  <th className="pb-3 font-mono text-xs">AI</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]">
                {filtered.map((f) => (
                  <tr key={f.id} className="hover:bg-[var(--color-bg-tertiary)]/30 transition-colors">
                    <td className="py-3">
                      <p className="text-white font-medium font-mono text-xs">{f.title}</p>
                      <p className="text-xs text-[var(--color-text-secondary)] line-clamp-1 mt-0.5 font-mono">{f.description}</p>
                    </td>
                    <td className="py-3"><Badge text={f.severity} variant="severity" /></td>
                    <td className="py-3 text-[var(--color-text-secondary)] font-mono text-xs">{f.host || '-'}</td>
                    <td className="py-3 text-white font-mono text-xs">{f.risk_score?.toFixed(1) ?? '-'}</td>
                    <td className="py-3"><Badge text={f.status} variant="status" /></td>
                    <td className="py-3 text-[var(--color-text-secondary)] font-mono text-xs">{formatDate(f.created_at)}</td>
                    <td className="py-3">
                      <button
                        onClick={() => { setAnalyzingId(f.id); setAnalyzingTitle(f.title) }}
                        className="flex items-center gap-1 px-2 py-1 rounded-sm text-xs font-mono transition-all"
                        style={{ border: '1px solid rgba(0,255,65,0.3)', color: 'var(--neon-green)', background: 'rgba(0,255,65,0.05)', cursor: 'pointer' }}
                        title="Analyze with AI">
                        <Bot className="w-3 h-3" />
                        analyze
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {analyzingId !== null && (
        <AIAnalysisModal
          findingId={analyzingId}
          findingTitle={analyzingTitle}
          onClose={() => setAnalyzingId(null)}
        />
      )}
    </div>
  )
}
