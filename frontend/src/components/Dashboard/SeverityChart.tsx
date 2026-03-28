import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import type { DashboardStats } from '../../types'

const COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#f59e0b',
  low: '#3b82f6',
  info: '#6b7280',
}

export default function SeverityChart({ stats }: { stats: DashboardStats }) {
  const data = Object.entries(stats.findings_by_severity)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }))

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-[var(--color-text-secondary)] text-sm">
        No findings yet
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie data={data} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={2} dataKey="value">
          {data.map((entry) => (
            <Cell key={entry.name} fill={COLORS[entry.name] || '#6b7280'} />
          ))}
        </Pie>
        <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#f8fafc' }} />
        <Legend formatter={(value) => <span className="text-[var(--color-text-secondary)] capitalize text-sm">{value}</span>} />
      </PieChart>
    </ResponsiveContainer>
  )
}
