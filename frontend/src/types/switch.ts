export type SwitchConnectionState =
  | 'disabled'
  | 'unconfigured'
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'error'

export interface SwitchStatusData {
  enabled: boolean
  configured: boolean
  state: SwitchConnectionState
  connected: boolean
  agent_id?: string | null
  last_connected_at?: string | null
  last_error_at?: string | null
  last_error?: string | null
}

