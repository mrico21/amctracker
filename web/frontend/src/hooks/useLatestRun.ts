import { useQuery } from '@tanstack/react-query'
import { apiClient, ApiError } from '@/api/client'
import type { RunResult } from '@/api/types'
import { queryKeys } from '@/lib/queryKeys'

export function useLatestRun() {
  return useQuery<RunResult | null>({
    queryKey: queryKeys.latestRun(),
    queryFn: async () => {
      try {
        return await apiClient.latestRun()
      } catch (err) {
        // 404 means no runs have been completed yet — not an error
        if (err instanceof ApiError && err.status === 404) return null
        throw err
      }
    },
    staleTime: 60_000,
  })
}
