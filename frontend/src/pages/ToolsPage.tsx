import { useEffect, useState } from 'react'
import { Wrench, Play, ChevronDown, ChevronUp } from 'lucide-react'
import { toolService } from '../services/toolService'
import type { Tool } from '../types'
import Card from '../components/Common/Card'
import Loading from '../components/Common/Loading'
import EmptyState from '../components/Common/EmptyState'

export default function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    toolService.listAvailable().then(setTools).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading text="Loading tools..." />

  const categories = [...new Set(tools.map((t) => t.category))]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white">Security Tools</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">{tools.length} tools available</p>
      </div>

      {tools.length === 0 ? (
        <EmptyState icon={<Wrench className="w-12 h-12" />} title="No tools configured" description="Tools will appear here once configured by admin." />
      ) : (
        categories.map((cat) => (
          <Card key={cat} title={cat || 'General'}>
            <div className="divide-y divide-[var(--color-border)] -mt-2">
              {tools.filter((t) => t.category === cat).map((tool) => (
                <div key={tool.name} className="py-3">
                  <div className="flex items-center justify-between cursor-pointer" onClick={() => setExpanded(expanded === tool.name ? null : tool.name)}>
                    <div className="flex items-center gap-3">
                      <div className={`w-2 h-2 rounded-full ${tool.available ? 'bg-green-400' : 'bg-gray-500'}`} />
                      <div>
                        <p className="text-white font-medium">{tool.name}</p>
                        <p className="text-xs text-[var(--color-text-secondary)]">{tool.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {tool.available && (
                        <button className="p-1.5 text-green-400 hover:bg-green-400/10 rounded" title="Execute" onClick={(e) => { e.stopPropagation() }}>
                          <Play className="w-4 h-4" />
                        </button>
                      )}
                      {expanded === tool.name ? <ChevronUp className="w-4 h-4 text-[var(--color-text-secondary)]" /> : <ChevronDown className="w-4 h-4 text-[var(--color-text-secondary)]" />}
                    </div>
                  </div>
                  {expanded === tool.name && tool.parameters && (
                    <div className="mt-3 ml-5 p-3 bg-[var(--color-bg-tertiary)]/50 rounded-lg text-xs">
                      <p className="text-[var(--color-text-secondary)] font-medium mb-2">Parameters:</p>
                      {tool.parameters.map((p) => (
                        <div key={p.name} className="flex items-center gap-2 mb-1">
                          <span className="text-indigo-400 font-mono">{p.name}</span>
                          <span className="text-[var(--color-text-secondary)]">({p.type})</span>
                          {p.required && <span className="text-red-400">*</span>}
                          <span className="text-[var(--color-text-secondary)]"> - {p.description}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        ))
      )}
    </div>
  )
}
