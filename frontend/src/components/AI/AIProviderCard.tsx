import { useState, useEffect, useCallback } from 'react'
import { Wifi, WifiOff, Loader2, ChevronDown, ChevronUp, Download } from 'lucide-react'
import { aiService, type AIConfig, type AIConfigUpdate, type AIProviderMeta, type AITestResult } from '../../services/aiService'

const INSTALL_LINKS: Partial<Record<string, { label: string; url: string }>> = {
  ollama: { label: 'Install Ollama', url: 'https://ollama.com/download' },
  lmstudio: { label: 'Download LM Studio', url: 'https://lmstudio.ai/' },
}

interface AIProviderCardProps {
  meta: AIProviderMeta
  config?: AIConfig
  onSaved: (cfg: AIConfig) => void
}

export default function AIProviderCard({ meta, config, onSaved }: AIProviderCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState(config?.base_url || meta.default_url || '')
  const [model, setModel] = useState(config?.model || '')
  const [enabled, setEnabled] = useState(config?.is_enabled ?? false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<AITestResult | null>(null)
  const [availableModels, setAvailableModels] = useState<string[]>([])

  const isLocal = meta.type === 'local'

  const handleTest = useCallback(async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const result = await aiService.testProvider(meta.provider)
      setTestResult(result)
      if (result.models.length > 0) setAvailableModels(result.models)
    } catch {
      setTestResult({ provider: meta.provider, available: false, models: [], error: 'Request failed' })
    } finally {
      setTesting(false)
    }
  }, [meta.provider])

  // Auto-test local providers on mount
  useEffect(() => {
    if (isLocal) handleTest()
  }, [isLocal, handleTest])

  const handleSave = async () => {
    setSaving(true)
    try {
      const payload: AIConfigUpdate = { is_enabled: enabled, model, base_url: baseUrl || undefined }
      if (apiKey) payload.api_key = apiKey
      const saved = await aiService.updateConfig(meta.provider, payload)
      onSaved(saved)
      setApiKey('')
    } finally {
      setSaving(false)
    }
  }

  const statusColor = testResult === null ? 'var(--color-text-secondary)'
    : testResult.available ? 'var(--neon-green)' : 'var(--neon-red)'

  return (
    <div className="rounded-lg overflow-hidden transition-all duration-200"
      style={{ border: `1px solid ${enabled ? 'var(--neon-green)' : 'var(--color-border)'}`, background: 'var(--color-bg-tertiary)' }}>

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center gap-3">
          {testResult !== null ? (
            testResult.available
              ? <Wifi className="w-4 h-4 neon-pulse" style={{ color: 'var(--neon-green)' }} />
              : <WifiOff className="w-4 h-4" style={{ color: 'var(--neon-red)' }} />
          ) : (
            <div className="w-2 h-2 rounded-full" style={{ background: enabled ? 'var(--neon-green)' : 'var(--color-text-secondary)' }} />
          )}
          <span className="text-white font-mono text-sm font-medium">{meta.label}</span>
          <span className="text-xs font-mono px-2 py-0.5 rounded-sm"
            style={{ background: 'rgba(0,255,65,0.08)', color: 'var(--neon-green)', border: '1px solid rgba(0,255,65,0.2)' }}>
            {meta.type}
          </span>
          {config?.has_api_key && (
            <span className="text-xs font-mono px-2 py-0.5 rounded-sm"
              style={{ background: 'rgba(0,212,255,0.08)', color: 'var(--neon-blue)', border: '1px solid rgba(0,212,255,0.2)' }}>
              key saved
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer" onClick={(e) => e.stopPropagation()}>
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} className="w-4 h-4" />
            <span className="text-xs font-mono" style={{ color: enabled ? 'var(--neon-green)' : 'var(--color-text-secondary)' }}>
              {enabled ? 'enabled' : 'disabled'}
            </span>
          </label>
          {expanded ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
        </div>
      </div>

      {/* Expanded form */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-[var(--color-border)]">
          <div className="pt-3" />

          {(isLocal || meta.type === 'custom') && (
            <div>
              <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">Base URL</label>
              <input
                type="text" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
                placeholder={meta.default_url || 'http://localhost:11434'}
                className="w-full px-3 py-2 rounded-sm text-sm font-mono text-white focus:outline-none"
                style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}
                onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'}
              />
            </div>
          )}

          {!isLocal && (
            <div>
              <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">
                API Key {config?.has_api_key && <span style={{ color: 'var(--neon-green)' }}>(saved — enter new to replace)</span>}
              </label>
              <input
                type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                placeholder={config?.has_api_key ? '••••••••••••••••' : 'sk-...'}
                className="w-full px-3 py-2 rounded-sm text-sm font-mono text-white focus:outline-none"
                style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}
                onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'}
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-mono text-[var(--color-text-secondary)] mb-1">Model</label>
            {availableModels.length > 0 ? (
              <select value={model} onChange={(e) => setModel(e.target.value)}
                className="w-full px-3 py-2 rounded-sm text-sm font-mono text-white focus:outline-none"
                style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}>
                <option value="">-- select model --</option>
                {availableModels.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            ) : (
              <input
                type="text" value={model} onChange={(e) => setModel(e.target.value)}
                placeholder="e.g. llama3.2, gpt-4o, claude-sonnet-4-6"
                className="w-full px-3 py-2 rounded-sm text-sm font-mono text-white focus:outline-none"
                style={{ background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)' }}
                onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'}
              />
            )}
          </div>

          {testResult && (
            <div className="text-xs font-mono p-2 rounded-sm" style={{
              background: testResult.available ? 'rgba(0,255,65,0.05)' : 'rgba(255,0,64,0.05)',
              border: `1px solid ${testResult.available ? 'var(--neon-green)' : 'var(--neon-red)'}`,
              color: statusColor,
            }}>
              {testResult.available
                ? `✓ Connected — ${testResult.models.length} model(s) available`
                : `✗ ${testResult.error ?? 'Not reachable'}`}
              {!testResult.available && isLocal && INSTALL_LINKS[meta.provider] && (
                <a
                  href={INSTALL_LINKS[meta.provider]!.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 mt-2 underline"
                  style={{ color: 'var(--neon-blue)' }}
                >
                  <Download className="w-3 h-3" />
                  {INSTALL_LINKS[meta.provider]!.label}
                </a>
              )}
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <button onClick={handleTest} disabled={testing}
              className="px-3 py-1.5 rounded-sm text-xs font-mono transition-all flex items-center gap-1.5 disabled:opacity-40"
              style={{ border: '1px solid var(--neon-blue)', color: 'var(--neon-blue)', background: 'transparent', cursor: 'pointer' }}>
              {testing ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
              {testing ? 'testing...' : 'test connection'}
            </button>
            <button onClick={handleSave} disabled={saving} className="px-3 py-1.5 rounded-sm text-xs font-mono btn-neon flex items-center gap-1.5">
              {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
              {saving ? 'saving...' : 'save'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
