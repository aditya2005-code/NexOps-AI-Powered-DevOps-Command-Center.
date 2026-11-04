import api from '@/services/api'
import type { BackendIncident, IncidentEvent, IncidentStats } from '@/types/incident'

interface ApiResponse<T> {
  success: boolean
  message: string
  data: T
}

export interface IncidentQueryParams {
  skip?: number
  limit?: number
  status?: string
  severity?: string
  project_id?: string
}

export const incidentService = {
  async list(params?: IncidentQueryParams): Promise<BackendIncident[]> {
    const response = await api.get<ApiResponse<BackendIncident[]>>('/incidents', { params })
    return response.data.data
  },

  async getById(id: string): Promise<BackendIncident> {
    const response = await api.get<ApiResponse<BackendIncident>>(`/incidents/${id}`)
    return response.data.data
  },

  async listEvents(id: string): Promise<IncidentEvent[]> {
    const response = await api.get<ApiResponse<IncidentEvent[]>>(`/incidents/${id}/events`)
    return response.data.data
  },

  async getStats(): Promise<IncidentStats> {
    const response = await api.get<ApiResponse<IncidentStats>>('/incidents/stats/summary')
    return response.data.data
  },
}

