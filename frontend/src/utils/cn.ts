import { clsx, type ClassValue } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function severityColor(severity: string): string {
  const colors: Record<string, string> = {
    critical: 'text-[#ff0040] bg-[#ff0040]/10 border-[#ff0040]/30',
    high:     'text-[#ff6b00] bg-[#ff6b00]/10 border-[#ff6b00]/30',
    medium:   'text-[#ffd000] bg-[#ffd000]/10 border-[#ffd000]/30',
    low:      'text-[#00d4ff] bg-[#00d4ff]/10 border-[#00d4ff]/30',
    info:     'text-gray-400  bg-gray-400/10  border-gray-400/20',
  }
  return colors[severity] || colors.info
}

export function statusColor(status: string): string {
  const colors: Record<string, string> = {
    running:   'text-[#00d4ff] bg-[#00d4ff]/10 border-[#00d4ff]/30',
    completed: 'text-[#00ff41] bg-[#00ff41]/10 border-[#00ff41]/30',
    failed:    'text-[#ff0040] bg-[#ff0040]/10 border-[#ff0040]/30',
    pending:   'text-[#ffd000] bg-[#ffd000]/10 border-[#ffd000]/30',
    cancelled: 'text-gray-400  bg-gray-400/10  border-gray-400/20',
  }
  return colors[status] || colors.pending
}

export function formatDate(date: string | null): string {
  if (!date) return '-'
  return new Date(date).toLocaleString()
}
