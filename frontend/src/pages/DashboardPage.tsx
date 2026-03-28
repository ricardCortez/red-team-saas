import { useEffect, useState } from 'react'
import { dashboardService } from '../services/dashboardService'
import type { DashboardStats } from '../types'
import StatsGrid from '../components/Dashboard/StatsGrid'
import SeverityChart from '../components/Dashboard/SeverityChart'
import RecentScans from '../components/Dashboard/RecentScans'
import RecentFindings from '../components/Dashboard/RecentFindings'
import Card from '../components/Common/Card'
import Loading from '../components/Common/Loading'

const defaultStats: DashboardStats = {
  total_projects: 0, total_scans: 0, total_findings: 0, active_scans: 0,
  findings_by_severity: { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
  recent_scans: [], recent_findings: [], compliance_score: 0,
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>(defaultStats)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    dashboardService.getStats()
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading text="Loading dashboard..." />

  return (
    <div className="space-y-6">
      <StatsGrid stats={stats} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Findings by Severity">
          <SeverityChart stats={stats} />
        </Card>

        <Card title="Compliance Score">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="text-5xl font-bold text-white">{stats.compliance_score}%</div>
              <p className="text-[var(--color-text-secondary)] mt-2">Overall Compliance</p>
              <div className="w-48 h-2 bg-[var(--color-bg-tertiary)] rounded-full mt-4">
                <div className="h-2 bg-green-500 rounded-full transition-all" style={{ width: `${stats.compliance_score}%` }} />
              </div>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Recent Scans">
          <RecentScans scans={stats.recent_scans} />
        </Card>
        <Card title="Recent Findings">
          <RecentFindings findings={stats.recent_findings} />
        </Card>
      </div>
    </div>
  )
}
