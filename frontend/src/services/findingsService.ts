import api from './api'
import type { Finding } from '../types'

export const findingsService = {
  async list(params?: Record<string, unknown>): Promise<Finding[]> {
    const { data } = await api.get('/findings/', { params })
    return Array.isArray(data) ? data : data.items ?? []
  },

  async get(id: number): Promise<Finding> {
    const { data } = await api.get(`/findings/${id}`)
    return data
  },

  async updateStatus(id: number, status: string): Promise<Finding> {
    const { data } = await api.patch(`/findings/${id}`, { status })
    return data
  },
}
