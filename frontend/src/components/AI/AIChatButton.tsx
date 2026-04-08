import { Bot } from 'lucide-react'
import { useAIStore } from '../../store/aiStore'

export default function AIChatButton() {
  const { toggleChat, isOpen } = useAIStore()

  return (
    <button
      onClick={toggleChat}
      className="fixed bottom-6 right-6 w-12 h-12 rounded-sm flex items-center justify-center transition-all duration-200 z-50"
      style={{
        background: isOpen ? 'var(--neon-green)' : 'var(--color-bg-secondary)',
        border: '1px solid var(--neon-green)',
        boxShadow: isOpen ? 'var(--glow-green)' : '0 0 12px rgba(0,255,65,0.3)',
        color: isOpen ? '#0a0f1e' : 'var(--neon-green)',
        cursor: 'pointer',
      }}
      title="AI Assistant"
    >
      <Bot className="w-5 h-5" />
    </button>
  )
}
