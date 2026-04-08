import { useEffect, useState } from 'react'
import { X, Loader2, Bot } from 'lucide-react'
import { aiService, type FindingAnalysis } from '../../services/aiService'

interface AIAnalysisModalProps {
  findingId: number
  findingTitle: string
  onClose: () => void
}

export default function AIAnalysisModal({ findingId, findingTitle, onClose }: AIAnalysisModalProps) {
  const [analysis, setAnalysis] = useState<FindingAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    aiService.analyzeFinding(findingId)
      .then(setAnalysis)
      .catch((err) => setError(err?.response?.data?.detail || 'Analysis failed. Is an AI provider enabled?'))
      .finally(() => setLoading(false))
  }, [findingId])

  const severityColor: Record<string, string> = {
    critical: 'var(--neon-red)',
    high: '#ff6b00',
    medium: '#ffd000',
    low: 'var(--neon-blue)',
    info: 'var(--color-text-secondary)',
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.8)' }} onClick={onClose}>
      <div className="w-full max-w-lg rounded-sm overflow-hidden"
        style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--neon-green)', boxShadow: 'var(--glow-green)' }}
        onClick={(e) => e.stopPropagation()}>

        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2">
            <Bot className="w-4 h-4" style={{ color: 'var(--neon-green)' }} />
            <span className="text-sm font-mono font-semibold" style={{ color: 'var(--neon-green)' }}>AI Analysis</span>
          </div>
          <button onClick={onClose} className="text-[var(--color-text-secondary)] hover:text-[var(--neon-red)] transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5">
          <p className="text-xs font-mono text-[var(--color-text-secondary)] mb-4 truncate">{findingTitle}</p>

          {loading && (
            <div className="flex items-center gap-3 text-sm font-mono" style={{ color: 'var(--neon-green)' }}>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing with AI...
            </div>
          )}

          {error && (
            <div className="text-xs font-mono p-3 rounded-sm"
              style={{ background: 'rgba(255,0,64,0.05)', border: '1px solid var(--neon-red)', color: 'var(--neon-red)' }}>
              ✗ {error}
            </div>
          )}

          {analysis && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-3 rounded-sm"
                style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }}>
                <span className="text-xs font-mono text-[var(--color-text-secondary)]">Severity:</span>
                <span className="text-sm font-mono font-bold capitalize"
                  style={{ color: severityColor[analysis.severity] || 'var(--color-text)' }}>
                  {analysis.severity}
                </span>
                <span className="ml-auto text-xs font-mono text-[var(--color-text-secondary)]">
                  via {analysis.provider} / {analysis.model}
                </span>
              </div>

              <div>
                <p className="text-xs font-mono mb-2" style={{ color: 'var(--neon-blue)' }}>// Explanation</p>
                <p className="text-xs font-mono text-[var(--color-text)] leading-relaxed whitespace-pre-wrap p-3 rounded-sm"
                  style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }}>
                  {analysis.explanation}
                </p>
              </div>

              <div>
                <p className="text-xs font-mono mb-2" style={{ color: 'var(--neon-green)' }}>// Remediation</p>
                <p className="text-xs font-mono text-[var(--color-text)] leading-relaxed whitespace-pre-wrap p-3 rounded-sm"
                  style={{ background: 'var(--color-bg-tertiary)', border: '1px solid rgba(0,255,65,0.2)' }}>
                  {analysis.remediation}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
