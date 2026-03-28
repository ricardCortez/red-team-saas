import { useEffect, useState } from 'react'
import { Globe, RefreshCw } from 'lucide-react'
import api from '../services/api'
import Card from '../components/Common/Card'
import Badge from '../components/Common/Badge'
import Loading from '../components/Common/Loading'
import EmptyState from '../components/Common/EmptyState'
import { formatDate } from '../utils/cn'

interface ThreatIntelEntry {
  id: number
  indicator: string
  indicator_type: string
  severity: string
  source: string
  description: string
  created_at: string
}

export default function ThreatIntelPage() {
  const [entries, setEntries] = useState<ThreatIntelEntry[]>([])
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    api.get('/threat-intel/')
      .then((r) => setEntries(Array.isArray(r.data) ? r.data : r.data.items ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) return <Loading text="Loading threat intelligence..." />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white">Threat Intelligence</h2>
        <button onClick={load} className="px-3 py-2 bg-[var(--color-bg-tertiary)] text-white rounded-lg text-sm flex items-center gap-2">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {entries.length === 0 ? (
        <EmptyState icon={<Globe className="w-12 h-12" />} title="No threat intel data" description="Threat intelligence feeds will populate as scans produce results." />
      ) : (
        <Card>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[var(--color-text-secondary)] border-b border-[var(--color-border)]">
                <th className="pb-3 font-medium">Indicator</th>
                <th className="pb-3 font-medium">Type</th>
                <th className="pb-3 font-medium">Severity</th>
                <th className="pb-3 font-medium">Source</th>
                <th className="pb-3 font-medium">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)]">
              {entries.map((e) => (
                <tr key={e.id} className="hover:bg-[var(--color-bg-tertiary)]/30">
                  <td className="py-3 text-white font-mono text-xs">{e.indicator}</td>
                  <td className="py-3 text-[var(--color-text-secondary)] uppercase text-xs">{e.indicator_type}</td>
                  <td className="py-3"><Badge text={e.severity} variant="severity" /></td>
                  <td className="py-3 text-[var(--color-text-secondary)]">{e.source}</td>
                  <td className="py-3 text-[var(--color-text-secondary)]">{formatDate(e.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}
