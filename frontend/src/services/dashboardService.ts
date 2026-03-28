import api from './api'
import type { DashboardStats } from '../types'

export const dashboardService = {
  async getStats(): Promise<DashboardStats> {
    try {
      const { data } = await api.get('/dashboard/stats')
      return data
    } catch {
      // Fallback: aggregate from multiple endpoints
      const [scans, findings] = await Promise.allSettled([
        api.get('/scans/'),
        api.get('/findings/'),
      ])

      const scanList = scans.status === 'fulfilled' ? (Array.isArray(scans.value.data) ? scans.value.data : scans.value.data?.items ?? []) : []
      const findingList = findings.status === 'fulfilled' ? (Array.isArray(findings.value.data) ? findings.value.data : findings.value.data?.items ?? []) : []

      return {
        total_projects: 0,
        total_scans: scanList.length,
        total_findings: findingList.length,
        active_scans: scanList.filter((s: { status: string }) => s.status === 'running').length,
        findings_by_severity: {
          critical: findingList.filter((f: { severity: string }) => f.severity === 'critical').length,
          high: findingList.filter((f: { severity: string }) => f.severity === 'high').length,
          medium: findingList.filter((f: { severity: string }) => f.severity === 'medium').length,
          low: findingList.filter((f: { severity: string }) => f.severity === 'low').length,
          info: findingList.filter((f: { severity: string }) => f.severity === 'info').length,
        },
        recent_scans: scanList.slice(0, 5),
        recent_findings: findingList.slice(0, 5),
        compliance_score: 0,
      }
    }
  },
}
