import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

export function useWatchlist(id: string) {
  return useQuery({
    queryKey: queryKeys.watchlist(id),
    queryFn: () => apiClient.watchlist(id),
    enabled: id.length > 0,
    staleTime: 60_000,
  })
}
