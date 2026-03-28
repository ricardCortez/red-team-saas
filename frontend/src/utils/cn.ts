import { clsx, type ClassValue } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function severityColor(severity: string): string {
  const colors: Record<string, string> = {
    critical: 'text-red-500 bg-red-500/10',
    high: 'text-orange-500 bg-orange-500/10',
    medium: 'text-yellow-500 bg-yellow-500/10',
    low: 'text-blue-500 bg-blue-500/10',
    info: 'text-gray-400 bg-gray-400/10',
  }
  return colors[severity] || colors.info
}

export function statusColor(status: string): string {
  const colors: Record<string, string> = {
    running: 'text-blue-400 bg-blue-400/10',
    completed: 'text-green-400 bg-green-400/10',
    failed: 'text-red-400 bg-red-400/10',
    pending: 'text-yellow-400 bg-yellow-400/10',
    cancelled: 'text-gray-400 bg-gray-400/10',
  }
  return colors[status] || colors.pending
}

export function formatDate(date: string | null): string {
  if (!date) return '-'
  return new Date(date).toLocaleString()
}
