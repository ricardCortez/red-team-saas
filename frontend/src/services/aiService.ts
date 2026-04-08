import api from './api'

export interface AIProviderMeta {
  provider: string
  label: string
  type: 'local' | 'cloud' | 'custom'
  default_url: string | null
}

export interface AIConfig {
  provider: string
  is_enabled: boolean
  has_api_key: boolean
  base_url: string | null
  model: string
  label: string | null
}

export interface AIConfigUpdate {
  is_enabled: boolean
  api_key?: string
  base_url?: string
  model: string
  label?: string
}

export interface AITestResult {
  provider: string
  available: boolean
  models: string[]
  error: string | null
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface ChatResponse {
  reply: string
  provider: string
  model: string
}

export interface FindingAnalysis {
  severity: string
  explanation: string
  remediation: string
  provider: string
  model: string
}

export const aiService = {
  getProviders: () =>
    api.get<AIProviderMeta[]>('/ai/providers').then((r) => r.data),

  getConfigs: () =>
    api.get<AIConfig[]>('/ai/config').then((r) => r.data),

  updateConfig: (provider: string, data: AIConfigUpdate) =>
    api.put<AIConfig>(`/ai/config/${provider}`, data).then((r) => r.data),

  testProvider: (provider: string) =>
    api.post<AITestResult>(`/ai/test/${provider}`).then((r) => r.data),

  chat: (messages: ChatMessage[], provider?: string, model?: string) =>
    api.post<ChatResponse>('/ai/chat', { messages, provider, model }).then((r) => r.data),

  analyzeFinding: (findingId: number) =>
    api.post<FindingAnalysis>(`/ai/analyze/finding/${findingId}`).then((r) => r.data),
}
