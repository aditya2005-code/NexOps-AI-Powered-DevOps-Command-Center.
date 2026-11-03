export interface HealthResponse {
  status: string
  version: string
  environment: string
}

export type IncidentSeverity = 'critical' | 'high' | 'medium' | 'low'
export type IncidentStatus = 'open' | 'investigating' | 'awaiting_approval' | 'resolved'

export interface Incident {
  id: string
  title: string
  project: string
  severity: IncidentSeverity
  status: IncidentStatus
  detectedAt: string
  assignedAgent: string
  summary: string
  affectedServices: string[]
  rootCauseCandidate?: string
}

export type AgentStatus = 'idle' | 'working' | 'waiting_for_approval' | 'offline'

export interface Agent {
  id: string
  name: string
  role: string
  status: AgentStatus
  lastActivity: string
  description: string
  capabilities: string[]
  currentTask?: string
}

export type ProjectHealth = 'healthy' | 'degraded' | 'critical'

export interface Project {
  id: string
  name: string
  repository: string
  environment: 'production' | 'staging' | 'preview'
  status: 'active' | 'maintenance' | 'paused'
  health: ProjectHealth
  lastActivity: string
  activeIncidentsCount: number
  servicesCount: number
}

export type ActivityEventType =
  | 'incident_detected'
  | 'log_analyzed'
  | 'root_cause_found'
  | 'patch_generated'
  | 'approval_requested'
  | 'test_completed'

export interface ActivityEvent {
  id: string
  type: ActivityEventType
  title: string
  description: string
  timestamp: string
  agentName: string
  incidentId?: string
  status: 'success' | 'warning' | 'in_progress' | 'critical'
}

export interface AuditLogEntry {
  id: string
  timestamp: string
  actor: string
  actorType: 'user' | 'agent' | 'system'
  action: string
  resource: string
  status: 'success' | 'failure' | 'pending'
  ipAddress?: string
}

export interface MetricCardData {
  id: string
  title: string
  value: string
  change: string
  isPositive: boolean
  indicator: 'normal' | 'alert' | 'warning' | 'success'
  description: string
}
