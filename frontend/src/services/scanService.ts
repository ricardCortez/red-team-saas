import api from './api'
import type { Scan } from '../types'

export const scanService = {
  async list(params?: Record<string, unknown>): Promise<Scan[]> {
    const { data } = await api.get('/scans/', { params })
    return Array.isArray(data) ? data : data.items ?? []
  },

  async get(id: number): Promise<Scan> {
    const { data } = await api.get(`/scans/${id}`)
    return data
  },

  async create(scan: Partial<Scan>): Promise<Scan> {
    const { data } = await api.post('/scans/', scan)
    return data
  },

  async cancel(id: number): Promise<void> {
    await api.post(`/scans/${id}/cancel`)
  },

  async run(id: number): Promise<Scan> {
    const { data } = await api.post(`/scans/${id}/run`)
    return data
  },
}
