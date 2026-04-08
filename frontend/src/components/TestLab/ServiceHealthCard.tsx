import { RefreshCw } from 'lucide-react';

type HealthStatus = 'checking' | 'online' | 'offline';

interface ServiceHealthCardProps {
  name: string;
  status: HealthStatus;
  description?: string;
  onRecheck: () => void;
}

export function ServiceHealthCard({ name, status, description, onRecheck }: ServiceHealthCardProps) {
  const statusColor = {
    checking: 'text-yellow-400',
    online: 'text-[var(--color-neon-green)]',
    offline: 'text-[var(--color-neon-red)]',
  }[status];

  const dotColor = {
    checking: 'bg-yellow-400 animate-pulse',
    online: 'bg-[var(--color-neon-green)] animate-pulse',
    offline: 'bg-[var(--color-neon-red)]',
  }[status];

  return (
    <div className="flex items-center justify-between p-3 border border-white/10 rounded-lg bg-black/40 hover:border-white/20 transition-colors">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full shrink-0 ${dotColor}`} />
          <span className="font-mono text-sm text-white truncate">{name}</span>
        </div>
        {description && (
          <p className="text-xs text-gray-500 ml-4 mt-0.5 truncate">{description}</p>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0 ml-2">
        <span className={`text-xs font-mono ${statusColor}`}>
          {status === 'checking' ? '...' : status}
        </span>
        <button
          onClick={onRecheck}
          className="text-gray-500 hover:text-white transition-colors"
          title="Recheck"
        >
          <RefreshCw className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}
