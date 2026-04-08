import { create } from 'zustand'
import type { ChatMessage } from '../services/aiService'

interface AIState {
  isOpen: boolean
  messages: ChatMessage[]
  isLoading: boolean
  activeProvider: string | null
  pageContext: string
  toggleChat: () => void
  openChat: () => void
  closeChat: () => void
  addMessage: (msg: ChatMessage) => void
  setLoading: (v: boolean) => void
  setActiveProvider: (p: string | null) => void
  setPageContext: (ctx: string) => void
  clearMessages: () => void
}

export const useAIStore = create<AIState>((set) => ({
  isOpen: false,
  messages: [],
  isLoading: false,
  activeProvider: null,
  pageContext: '',

  toggleChat: () => set((s) => ({ isOpen: !s.isOpen })),
  openChat: () => set({ isOpen: true }),
  closeChat: () => set({ isOpen: false }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setLoading: (v) => set({ isLoading: v }),
  setActiveProvider: (p) => set({ activeProvider: p }),
  setPageContext: (ctx) => set({ pageContext: ctx }),
  clearMessages: () => set({ messages: [] }),
}))
