import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

export function useWatchlists() {
  return useQuery({
    queryKey: queryKeys.watchlists(),
    queryFn: () => apiClient.watchlists(),
    staleTime: 60_000,
  })
}
