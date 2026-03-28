import api from './api'
import type { Tool } from '../types'

export const toolService = {
  async listAvailable(): Promise<Tool[]> {
    const { data } = await api.get('/tools/available')
    return Array.isArray(data) ? data : data.tools ?? data ?? []
  },

  async getInfo(toolName: string): Promise<Tool> {
    const { data } = await api.get('/tools/info', { params: { tool_name: toolName } })
    return data
  },

  async execute(toolName: string, params: Record<string, unknown>): Promise<unknown> {
    const { data } = await api.post('/tools/execute', { tool_name: toolName, parameters: params })
    return data
  },
}
