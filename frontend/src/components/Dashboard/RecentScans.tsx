import { Link } from 'react-router-dom'
import type { Scan } from '../../types'
import Badge from '../Common/Badge'
import { formatDate } from '../../utils/cn'

export default function RecentScans({ scans }: { scans: Scan[] }) {
  if (scans.length === 0) {
    return <p className="text-sm text-[var(--color-text-secondary)] py-4">No recent scans</p>
  }

  return (
    <div className="divide-y divide-[var(--color-border)]">
      {scans.map((scan) => (
        <Link to={`/scans`} key={scan.id} className="flex items-center justify-between py-3 hover:bg-[var(--color-bg-tertiary)]/50 px-2 -mx-2 rounded transition-colors">
          <div>
            <p className="text-sm font-medium text-white">{scan.name || `Scan #${scan.id}`}</p>
            <p className="text-xs text-[var(--color-text-secondary)]">{scan.tool_name || scan.scan_type} &middot; {formatDate(scan.created_at)}</p>
          </div>
          <Badge text={scan.status} variant="status" />
        </Link>
      ))}
    </div>
  )
}
