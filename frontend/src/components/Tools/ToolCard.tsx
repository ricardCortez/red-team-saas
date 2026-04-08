import { useState } from 'react';
import { ChevronDown, ChevronUp, Play, AlertCircle } from 'lucide-react';
import type { ToolDefinition } from '../../data/toolDefinitions';
import { CATEGORY_COLORS } from '../../data/toolDefinitions';

interface ToolCardProps {
  tool: ToolDefinition;
  isAvailable?: boolean;
  onExecute: (tool: ToolDefinition) => void;
}

export function ToolCard({ tool, isAvailable = true, onExecute }: ToolCardProps) {
  const [expanded, setExpanded] = useState(false);
  const Icon = tool.icon;
  const categoryColor = CATEGORY_COLORS[tool.category];

  return (
    <div className="border border-white/10 rounded-lg bg-black/40 hover:border-[var(--color-neon-green)]/40 transition-all duration-200 hover:shadow-[0_0_12px_var(--color-neon-green)]/10">
      {/* Card Header */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          {/* Icon + Name + Category */}
          <div className="flex items-center gap-3 min-w-0">
            <div className="shrink-0 w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center">
              <Icon className="w-5 h-5 text-[var(--color-neon-green)]" />
            </div>
            <div className="min-w-0">
              <h3 className="font-mono text-sm font-bold text-[var(--color-neon-green)] truncate">
                {tool.name}
              </h3>
              <span className={`inline-block text-xs border px-1.5 py-0.5 rounded font-mono mt-0.5 ${categoryColor}`}>
                {tool.category}
              </span>
            </div>
          </div>

          {/* Status */}
          <div className="flex items-center gap-1.5 shrink-0">
            <span className={`w-2 h-2 rounded-full ${isAvailable ? 'bg-[var(--color-neon-green)] animate-pulse' : 'bg-gray-600'}`} />
            <span className="text-xs text-gray-400">{isAvailable ? 'available' : 'not installed'}</span>
          </div>
        </div>

        {/* Description */}
        <p className="text-xs text-gray-400 mt-3 leading-relaxed line-clamp-2">
          {tool.description}
        </p>

        {/* Actions */}
        <div className="flex items-center gap-2 mt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
          >
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            Details
          </button>

          <div className="flex-1" />

          {isAvailable ? (
            <button
              onClick={() => onExecute(tool)}
              className="flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 border border-[var(--color-neon-green)] text-[var(--color-neon-green)] rounded hover:bg-[var(--color-neon-green)] hover:text-black transition-all duration-150"
            >
              <Play className="w-3 h-3" />
              Execute
            </button>
          ) : (
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <AlertCircle className="w-3.5 h-3.5" />
              Not installed
            </div>
          )}
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="border-t border-white/10 px-4 py-3">
          <p className="text-xs text-gray-300 leading-relaxed mb-3">{tool.description}</p>
          {tool.parameters.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Parameters</p>
              <div className="space-y-1">
                {tool.parameters.map((param) => (
                  <div key={param.name} className="flex items-center gap-2 text-xs">
                    <span className="font-mono text-[var(--color-neon-blue)] w-32 shrink-0">{param.name}</span>
                    <span className="text-gray-500">{param.required ? 'required' : 'optional'}</span>
                    <span className="text-gray-600">·</span>
                    <span className="text-gray-400">{param.placeholder}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
