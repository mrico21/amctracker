import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

export function useSchedulerStatus() {
  return useQuery({
    queryKey: queryKeys.schedulerStatus(),
    queryFn: () => apiClient.schedulerStatus(),
    refetchInterval: 5_000,
  })
}
