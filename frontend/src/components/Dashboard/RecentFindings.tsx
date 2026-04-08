import { Link } from 'react-router-dom'
import type { Finding } from '../../types'
import Badge from '../Common/Badge'
import { formatDate } from '../../utils/cn'

export default function RecentFindings({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) {
    return <p className="text-sm text-[var(--color-text-secondary)] py-4">No findings yet</p>
  }

  return (
    <div className="divide-y divide-[var(--color-border)]">
      {findings.map((f) => (
        <Link to={`/findings`} key={f.id} className="flex items-center justify-between py-3 hover:bg-[var(--color-bg-tertiary)]/50 px-2 -mx-2 rounded transition-colors">
          <div className="min-w-0 mr-3">
            <p className="text-sm font-medium text-white truncate">{f.title}</p>
            <p className="text-xs text-[var(--color-text-secondary)]">{f.tool_name || f.host || 'Unknown source'} &middot; {formatDate(f.created_at)}</p>
          </div>
          <Badge text={f.severity} variant="severity" />
        </Link>
      ))}
    </div>
  )
}
