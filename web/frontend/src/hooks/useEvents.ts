import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

export function useEvents(isRunning: boolean) {
  return useQuery({
    queryKey: queryKeys.events(),
    queryFn: () => apiClient.events(),
    // Poll more frequently during an active run so the feed feels live
    refetchInterval: isRunning ? 2_000 : 15_000,
  })
}
