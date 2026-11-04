export type IncidentSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
export type IncidentStatus = 'OPEN' | 'INVESTIGATING' | 'AWAITING_APPROVAL' | 'RESOLVED'

export interface BackendIncident {
  id: string
  project_id: string
  project_name?: string | null
  title: string
  description?: string | null
  severity: IncidentSeverity
  status: IncidentStatus
  source: string
  source_id?: string | null
  root_cause_summary?: string | null
  detected_at: string
  resolved_at?: string | null
  created_at: string
  updated_at: string
}

export interface IncidentEvent {
  id: string
  incident_id: string
  event_type: string
  actor_type: string
  actor_identifier?: string | null
  description: string
  event_metadata: Record<string, unknown>
  created_at: string
}

export interface IncidentStats {
  total: number
  open: number
  investigating: number
  awaiting_approval: number
  resolved: number
}

