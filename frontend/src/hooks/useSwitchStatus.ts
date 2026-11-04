import { useQuery } from '@tanstack/react-query'
import { switchService } from '@/services/switchService'
import type { SwitchStatusData } from '@/types/switch'

export function useSwitchStatus() {
  return useQuery<SwitchStatusData, Error>({
    queryKey: ['switch-status'],
    queryFn: () => switchService.getStatus(),
    refetchInterval: 10000,
    refetchIntervalInBackground: false,
    staleTime: 5000,
  })
}
