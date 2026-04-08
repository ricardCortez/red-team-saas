import api from './api'

export interface PhishingCampaign {
  id: number
  project_id: number
  created_by: number
  name: string
  description?: string
  status: 'draft' | 'active' | 'completed' | 'cancelled'
  gophish_url: string
  gophish_campaign_id?: number
  template_name?: string
  landing_page_name?: string
  smtp_profile_name?: string
  target_group_name?: string
  phishing_url?: string
  launch_date?: string
  stats_total: number
  stats_sent: number
  stats_opened: number
  stats_clicked: number
  stats_submitted: number
  stats_last_synced?: string
  created_at: string
  updated_at: string
}

export interface PhishingTarget {
  id: number
  campaign_id: number
  email: string
  first_name?: string
  last_name?: string
  position?: string
  status: 'queued' | 'sent' | 'opened' | 'clicked' | 'submitted_data' | 'reported'
  created_at: string
}

export interface PhishingTargetResult {
  email: string
  status: string
  ip?: string
  latitude?: number
  longitude?: number
  reported: boolean
}

export interface GoPhishResources {
  templates: { id: number; name: string }[]
  pages: { id: number; name: string }[]
  smtp_profiles: { id: number; name: string }[]
  groups: { id: number; name: string }[]
}

export const phishingService = {
  async list(params?: Record<string, unknown>): Promise<{ items: PhishingCampaign[]; total: number }> {
    const { data } = await api.get('/phishing/campaigns/', { params })
    return data
  },

  async get(id: number): Promise<PhishingCampaign> {
    const { data } = await api.get(`/phishing/campaigns/${id}`)
    return data
  },

  async create(payload: Record<string, unknown>): Promise<PhishingCampaign> {
    const { data } = await api.post('/phishing/campaigns/', payload)
    return data
  },

  async update(id: number, payload: Record<string, unknown>): Promise<PhishingCampaign> {
    const { data } = await api.put(`/phishing/campaigns/${id}`, payload)
    return data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/phishing/campaigns/${id}`)
  },

  async addTargets(campaignId: number, targets: { email: string; first_name?: string; last_name?: string; position?: string }[]): Promise<PhishingTarget[]> {
    const { data } = await api.post(`/phishing/campaigns/${campaignId}/targets`, targets)
    return data
  },

  async listTargets(campaignId: number): Promise<PhishingTarget[]> {
    const { data } = await api.get(`/phishing/campaigns/${campaignId}/targets`)
    return data
  },

  async deleteTarget(campaignId: number, targetId: number): Promise<void> {
    await api.delete(`/phishing/campaigns/${campaignId}/targets/${targetId}`)
  },

  async launch(id: number): Promise<PhishingCampaign> {
    const { data } = await api.post(`/phishing/campaigns/${id}/launch`)
    return data
  },

  async stop(id: number): Promise<PhishingCampaign> {
    const { data } = await api.post(`/phishing/campaigns/${id}/stop`)
    return data
  },

  async getResults(id: number): Promise<{ results: PhishingTargetResult[]; stats: Record<string, number> }> {
    const { data } = await api.get(`/phishing/campaigns/${id}/results`)
    return data
  },

  async syncStats(id: number): Promise<PhishingCampaign> {
    const { data } = await api.post(`/phishing/campaigns/${id}/sync`)
    return data
  },

  async getGoPhishResources(gophishUrl: string, apiKey: string): Promise<GoPhishResources> {
    const { data } = await api.post('/phishing/campaigns/resources', {
      gophish_url: gophishUrl,
      gophish_api_key: apiKey,
    })
    return data
  },
}
