import { cn } from '../../utils/cn'
import type { ReactNode } from 'react'

interface CardProps {
  title?: string
  children: ReactNode
  className?: string
  action?: ReactNode
  glow?: 'green' | 'red' | 'blue' | false
}

export default function Card({ title, children, className, action, glow = false }: CardProps) {
  return (
    <div className={cn(
      'relative bg-[var(--color-bg-secondary)] rounded-xl border border-[var(--color-border)] overflow-hidden transition-all duration-300',
      'hover:border-[var(--neon-green)]/30',
      glow === 'green' && 'glow-green',
      glow === 'red' && 'glow-red',
      glow === 'blue' && 'glow-blue',
      className,
    )}>
      {title && (
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)]">
          <h3 className="text-sm font-semibold text-white tracking-wide uppercase font-mono">{title}</h3>
          {action}
        </div>
      )}
      <div className="p-6">{children}</div>
    </div>
  )
}
