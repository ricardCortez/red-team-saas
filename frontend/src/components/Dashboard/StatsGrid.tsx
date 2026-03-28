import { FolderOpen, Scan, Bug, AlertTriangle } from 'lucide-react'
import type { DashboardStats } from '../../types'

interface StatsGridProps {
  stats: DashboardStats
}

export default function StatsGrid({ stats }: StatsGridProps) {
  const items = [
    { label: 'Projects', value: stats.total_projects, icon: FolderOpen, color: 'text-blue-400', bg: 'bg-blue-400/10' },
    { label: 'Total Scans', value: stats.total_scans, icon: Scan, color: 'text-green-400', bg: 'bg-green-400/10' },
    { label: 'Findings', value: stats.total_findings, icon: Bug, color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
    { label: 'Active Scans', value: stats.active_scans, icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-400/10' },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {items.map((item) => (
        <div key={item.label} className="bg-[var(--color-bg-secondary)] rounded-xl border border-[var(--color-border)] p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--color-text-secondary)]">{item.label}</p>
              <p className="text-2xl font-bold text-white mt-1">{item.value}</p>
            </div>
            <div className={`p-3 rounded-lg ${item.bg}`}>
              <item.icon className={`w-5 h-5 ${item.color}`} />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
