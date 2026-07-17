import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

export function useTriggerRun() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => apiClient.triggerRun(),
    onSuccess: () => {
      // Immediately refetch info so run_in_progress reflects the new run
      void queryClient.invalidateQueries({ queryKey: queryKeys.info() })
    },
  })
}
