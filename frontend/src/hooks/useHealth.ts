import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'
import type { HealthResponse } from '@/types'

export function useHealth() {
  return useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: () => api.get<HealthResponse>('/health').then((r) => r.data),
    retry: false,
  })
}
