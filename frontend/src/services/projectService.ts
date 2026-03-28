import api from './api'
import type { Project } from '../types'

export const projectService = {
  async list(): Promise<Project[]> {
    const { data } = await api.get('/projects/')
    return Array.isArray(data) ? data : data.items ?? []
  },

  async get(id: number): Promise<Project> {
    const { data } = await api.get(`/projects/${id}`)
    return data
  },

  async create(project: Partial<Project>): Promise<Project> {
    const { data } = await api.post('/projects/', project)
    return data
  },

  async update(id: number, project: Partial<Project>): Promise<Project> {
    const { data } = await api.put(`/projects/${id}`, project)
    return data
  },

  async remove(id: number): Promise<void> {
    await api.delete(`/projects/${id}`)
  },
}
