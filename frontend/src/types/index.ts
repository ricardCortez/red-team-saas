// Auth
export interface User {
  id: number
  email: string
  username: string
  full_name: string | null
  is_active: boolean
  role: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  username: string
  password: string
  full_name: string
}

// Projects
export interface Project {
  id: number
  name: string
  description: string | null
  status: string
  created_at: string
  updated_at: string
  owner_id: number
}

// Targets
export interface Target {
  id: number
  name: string
  target_type: string
  value: string
  project_id: number
  status: string
  created_at: string
}

// Scans
export interface Scan {
  id: number
  name: string
  scan_type: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  target_id: number
  project_id: number
  tool_name: string | null
  parameters: Record<string, unknown>
  progress: number
  started_at: string | null
  completed_at: string | null
  created_at: string
}

// Findings
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info'

export interface Finding {
  id: number
  title: string
  description: string
  severity: Severity
  status: string
  scan_id: number
  target_id: number | null
  cve_id: string | null
  cvss_score: number | null
  evidence: string | null
  remediation: string | null
  created_at: string
}

// Reports
export interface Report {
  id: number
  name: string
  report_type: string
  format: string
  status: string
  project_id: number
  created_at: string
  file_url: string | null
}

// Compliance
export interface ComplianceFramework {
  id: number
  name: string
  version: string
  description: string
  total_controls: number
  compliant_controls: number
}

// Tools
export interface Tool {
  name: string
  category: string
  description: string
  available: boolean
  parameters: ToolParameter[]
}

export interface ToolParameter {
  name: string
  type: string
  required: boolean
  description: string
  default?: unknown
}

// Notifications
export interface Notification {
  id: number
  title: string
  message: string
  severity: Severity
  read: boolean
  created_at: string
}

// Alert Rules
export interface AlertRule {
  id: number
  name: string
  condition: string
  severity: Severity
  enabled: boolean
  channels: string[]
}

// Dashboard
export interface DashboardStats {
  total_projects: number
  total_scans: number
  total_findings: number
  active_scans: number
  findings_by_severity: Record<Severity, number>
  recent_scans: Scan[]
  recent_findings: Finding[]
  compliance_score: number
}

// Pagination
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pages: number
}

// WebSocket
export interface WSMessage {
  type: 'scan_progress' | 'scan_completed' | 'finding_new' | 'alert' | 'notification'
  payload: Record<string, unknown>
  timestamp: string
}
