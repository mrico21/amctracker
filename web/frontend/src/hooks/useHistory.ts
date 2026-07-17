import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

export function useHistory() {
  return useQuery({
    queryKey: queryKeys.history.all(),
    queryFn: () => apiClient.history(),
    staleTime: 30_000,
  })
}

export function useHistoryRun(runId: string) {
  return useQuery({
    queryKey: queryKeys.history.run(runId),
    queryFn: () => apiClient.historyRun(runId),
    staleTime: Infinity,
  })
}
