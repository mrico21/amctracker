import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

export function useTriggerRun() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => apiClient.triggerRun(),
    onSuccess: () => {
      // Immediately refetch info and job status to reflect the new run
      void queryClient.invalidateQueries({ queryKey: queryKeys.info() })
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobStatus() })
    },
  })
}
