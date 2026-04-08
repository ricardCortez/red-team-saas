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
        {frameworks.map((fw) => (
          <Card key={fw.id}>
            <div className="flex items-start gap-3 mb-4">
              <div className="p-2 bg-green-500/10 rounded-lg"><CheckCircle className="w-5 h-5 text-green-400" /></div>
              <div>
                <h3 className="text-white font-semibold">{fw.name}</h3>
                <p className="text-xs text-[var(--color-text-secondary)]">{fw.version} · {fw.framework_type}</p>
              </div>
            </div>
            {fw.description && (
              <p className="text-xs text-[var(--color-text-secondary)] mb-3">{fw.description}</p>
            )}
            <div className="flex justify-between text-xs mt-2">
              <span className="text-[var(--color-text-secondary)]">{fw.total_requirements} requirements</span>
              <span className="text-[var(--color-text-secondary)]">{new Date(fw.created_at).toLocaleDateString()}</span>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
