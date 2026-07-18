import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { SettingsResponse } from '@/api/types'
import { queryKeys } from '@/lib/queryKeys'

export function useUpdateSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<SettingsResponse>) => apiClient.updateSettings(body),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.settings(), data)
      // Scheduler status will refresh on its own poll interval
    },
  })
}
