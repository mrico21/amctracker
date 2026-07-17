import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health(),
    queryFn: () => apiClient.health(),
    staleTime: 60_000,
    refetchInterval: 120_000,
  })
}
