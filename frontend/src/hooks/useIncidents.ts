import { useQuery } from '@tanstack/react-query'
import { incidentService, type IncidentQueryParams } from '@/services/incidentService'
import type { BackendIncident, IncidentStats } from '@/types/incident'

export function useIncidents(params?: IncidentQueryParams) {
  return useQuery<BackendIncident[], Error>({
    queryKey: ['incidents', params],
    queryFn: () => incidentService.list(params),
    refetchInterval: 15000,
    refetchIntervalInBackground: false,
    staleTime: 10000,
  })
}

export function useIncidentDetail(id: string | null) {
  return useQuery<BackendIncident, Error>({
    queryKey: ['incident-detail', id],
    queryFn: () => incidentService.getById(id!),
    enabled: Boolean(id),
    staleTime: 10000,
  })
}

export function useIncidentStats() {
  return useQuery<IncidentStats, Error>({
    queryKey: ['incident-stats'],
    queryFn: () => incidentService.getStats(),
    refetchInterval: 15000,
    refetchIntervalInBackground: false,
    staleTime: 10000,
  })
}
