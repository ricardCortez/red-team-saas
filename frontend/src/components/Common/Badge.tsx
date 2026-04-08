import { cn, severityColor, statusColor } from '../../utils/cn'

interface BadgeProps {
  text: string
  variant?: 'severity' | 'status' | 'default'
  className?: string
}

export default function Badge({ text, variant = 'default', className }: BadgeProps) {
  const colorClass =
    variant === 'severity'
      ? severityColor(text)
      : variant === 'status'
        ? statusColor(text)
        : 'text-gray-300 bg-gray-500/10 border border-gray-500/20'

  return (
    <span className={cn(
      'inline-flex items-center px-2.5 py-0.5 rounded-sm text-xs font-mono font-medium capitalize border',
      colorClass,
      className,
    )}>
      {text}
    </span>
  )
}
