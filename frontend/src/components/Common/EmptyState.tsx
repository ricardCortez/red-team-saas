import type { ReactNode } from 'react'
import { InboxIcon } from 'lucide-react'

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
}

export default function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-[var(--color-text-secondary)] mb-4">
        {icon || <InboxIcon className="w-12 h-12" />}
      </div>
      <h3 className="text-lg font-medium text-white mb-2">{title}</h3>
      {description && <p className="text-sm text-[var(--color-text-secondary)] max-w-md mb-6">{description}</p>}
      {action}
    </div>
  )
}
