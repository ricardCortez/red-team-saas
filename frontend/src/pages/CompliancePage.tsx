import { useEffect, useState } from 'react'
import { Shield, CheckCircle } from 'lucide-react'
import api from '../services/api'
import type { ComplianceFramework } from '../types'
import Card from '../components/Common/Card'
import Loading from '../components/Common/Loading'
import EmptyState from '../components/Common/EmptyState'

export default function CompliancePage() {
  const [frameworks, setFrameworks] = useState<ComplianceFramework[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/compliance/frameworks')
      .then((r) => setFrameworks(Array.isArray(r.data) ? r.data : r.data.items ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading text="Loading compliance frameworks..." />

  if (frameworks.length === 0) {
    return <EmptyState icon={<Shield className="w-12 h-12" />} title="No compliance data" description="Compliance frameworks will appear once scan results are mapped." />
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-white">Compliance Frameworks</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {frameworks.map((fw) => {
          const pct = fw.total_controls > 0 ? Math.round((fw.compliant_controls / fw.total_controls) * 100) : 0
          return (
            <Card key={fw.id}>
              <div className="flex items-start gap-3 mb-4">
                <div className="p-2 bg-green-500/10 rounded-lg"><CheckCircle className="w-5 h-5 text-green-400" /></div>
                <div>
                  <h3 className="text-white font-semibold">{fw.name}</h3>
                  <p className="text-xs text-[var(--color-text-secondary)]">{fw.version}</p>
                </div>
              </div>
              <p className="text-xs text-[var(--color-text-secondary)] mb-3">{fw.description}</p>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-[var(--color-text-secondary)]">{fw.compliant_controls}/{fw.total_controls} controls</span>
                  <span className="text-white font-medium">{pct}%</span>
                </div>
                <div className="w-full h-2 bg-[var(--color-bg-tertiary)] rounded-full">
                  <div className={`h-2 rounded-full transition-all ${pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`} style={{ width: `${pct}%` }} />
                </div>
              </div>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
