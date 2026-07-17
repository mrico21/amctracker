import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

export function useInfo() {
  return useQuery({
    queryKey: queryKeys.info(),
    queryFn: () => apiClient.info(),
    // Poll more aggressively while a run is in progress
    refetchInterval: (query) => (query.state.data?.run_in_progress ? 5_000 : 30_000),
  })
}
