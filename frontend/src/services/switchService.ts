import api from '@/services/api'
import type { SwitchStatusData } from '@/types/switch'

interface ApiResponse<T> {
  success: boolean
  message: string
  data: T
}

export const switchService = {
  async getStatus(): Promise<SwitchStatusData> {
    const response = await api.get<ApiResponse<SwitchStatusData>>('/integrations/switch/status')
    return response.data.data
  },
}

