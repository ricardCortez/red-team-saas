import { cn } from '../../utils/cn'
import type { ReactNode } from 'react'

interface CardProps {
  title?: string
  children: ReactNode
  className?: string
  action?: ReactNode
}

export default function Card({ title, children, className, action }: CardProps) {
  return (
    <div className={cn('bg-[var(--color-bg-secondary)] rounded-xl border border-[var(--color-border)] overflow-hidden', className)}>
      {title && (
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)]">
          <h3 className="text-sm font-semibold text-white">{title}</h3>
          {action}
        </div>
      )}
      <div className="p-6">{children}</div>
    </div>
  )
}
