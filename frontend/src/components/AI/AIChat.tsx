import { useState, useRef, useEffect } from 'react'
import { X, Send, Trash2, Loader2 } from 'lucide-react'
import { useAIStore } from '../../store/aiStore'
import { aiService } from '../../services/aiService'

export default function AIChat() {
  const { isOpen, messages, isLoading, addMessage, setLoading, clearMessages, closeChat, pageContext } = useAIStore()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async () => {
    const text = input.trim()
    if (!text || isLoading) return
    setInput('')

    const userMsg = { role: 'user' as const, content: text }
    addMessage(userMsg)
    setLoading(true)

    try {
      const allMessages = [...messages, userMsg]
      const contextMessages = pageContext
        ? [{ role: 'system' as const, content: `Context: user is on the ${pageContext} page of a Red Team SaaS security platform.` }, ...allMessages]
        : allMessages
      const resp = await aiService.chat(contextMessages)
      addMessage({ role: 'assistant', content: resp.reply })
    } catch (err: any) {
      addMessage({ role: 'assistant', content: `✗ Error: ${err?.response?.data?.detail || 'No AI provider configured or request failed.'}` })
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  if (!isOpen) return null

  return (
    <div className="fixed bottom-22 right-6 w-96 rounded-sm flex flex-col z-50 overflow-hidden"
      style={{ height: '500px', background: 'var(--color-bg-secondary)', border: '1px solid var(--neon-green)', boxShadow: 'var(--glow-green)' }}>

      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full neon-pulse" style={{ background: 'var(--neon-green)' }} />
          <span className="text-sm font-mono font-semibold" style={{ color: 'var(--neon-green)' }}>AI Assistant</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={clearMessages} className="text-[var(--color-text-secondary)] hover:text-[var(--neon-red)] transition-colors">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          <button onClick={closeChat} className="text-[var(--color-text-secondary)] hover:text-[var(--neon-red)] transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-xs font-mono text-[var(--color-text-secondary)] mt-8">
            <p style={{ color: 'var(--neon-green)' }}>// AI Assistant ready</p>
            <p className="mt-1">Ask about security findings, request analysis,<br />or get remediation advice.</p>
          </div>
        )}
        {messages.filter(m => m.role !== 'system').map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className="max-w-[80%] px-3 py-2 rounded-sm text-xs font-mono whitespace-pre-wrap"
              style={m.role === 'user'
                ? { background: 'rgba(0,255,65,0.1)', border: '1px solid rgba(0,255,65,0.3)', color: 'var(--neon-green)' }
                : { background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}>
              {m.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="px-3 py-2 rounded-sm text-xs font-mono flex items-center gap-2"
              style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}>
              <Loader2 className="w-3 h-3 animate-spin" style={{ color: 'var(--neon-green)' }} />
              processing...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-3 border-t border-[var(--color-border)]">
        <div className="flex gap-2">
          <textarea
            value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKey}
            placeholder="// type your message..."
            rows={2}
            className="flex-1 px-3 py-2 rounded-sm text-xs font-mono text-white resize-none focus:outline-none"
            style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }}
            onFocus={(e) => e.target.style.borderColor = 'var(--neon-green)'}
            onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'}
          />
          <button onClick={send} disabled={isLoading || !input.trim()}
            className="px-3 rounded-sm transition-all flex items-center disabled:opacity-40"
            style={{ background: 'rgba(0,255,65,0.1)', border: '1px solid var(--neon-green)', color: 'var(--neon-green)', cursor: 'pointer' }}>
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
