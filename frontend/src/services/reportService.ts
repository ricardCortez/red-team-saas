import api from './api'
import type { Report } from '../types'

export const reportService = {
  async list(params?: Record<string, unknown>): Promise<Report[]> {
    const { data } = await api.get('/reports/', { params })
    return Array.isArray(data) ? data : data.items ?? []
  },

  async get(id: number): Promise<Report> {
    const { data } = await api.get(`/reports/${id}`)
    return data
  },

  async generate(reportData: Record<string, unknown>): Promise<Report> {
    const { data } = await api.post('/reports/generate', reportData)
    return data
  },

  async download(id: number): Promise<Blob> {
    const { data } = await api.get(`/reports/${id}/download`, { responseType: 'blob' })
    return data
  },
}
