import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

export function useTriggerRun() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      console.log('[DIAG] useTriggerRun: calling apiClient.triggerRun()')
      try {
        const result = await apiClient.triggerRun()
        console.log('[DIAG] useTriggerRun: triggerRun() resolved', result)
        return result
      } catch (err) {
        console.log('[DIAG] useTriggerRun: triggerRun() rejected', err)
        throw err
      }
    },
    onSuccess: (data) => {
      console.log('[DIAG] useTriggerRun onSuccess', data)
      // Immediately refetch info so run_in_progress reflects the new run
      void queryClient.invalidateQueries({ queryKey: queryKeys.info() })
    },
    onError: (err) => {
      console.log('[DIAG] useTriggerRun onError', err)
    },
  })
}
