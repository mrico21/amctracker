import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

export function useSettings() {
  return useQuery({
    queryKey: queryKeys.settings(),
    queryFn: () => apiClient.settings(),
    staleTime: 300_000,
  })
}
