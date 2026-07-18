import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

const TERMINAL_STATUSES = new Set(['idle', 'finished', 'failed', 'cancelled'])

export function useJobStatus(enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.jobStatus(),
    queryFn: () => apiClient.runStatus(),
    enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (!status || TERMINAL_STATUSES.has(status)) return false
      return 2000
    },
  })
}
