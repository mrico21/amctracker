import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { queryKeys } from '@/lib/queryKeys'

/**
 * Detects when run_in_progress transitions from true → false and invalidates
 * the latest run and history caches so the UI shows fresh data immediately.
 */
export function useRunCompletion(isRunning: boolean | undefined) {
  const queryClient = useQueryClient()
  const wasRunning = useRef(false)

  useEffect(() => {
    if (wasRunning.current && isRunning === false) {
      void queryClient.invalidateQueries({ queryKey: queryKeys.latestRun() })
      void queryClient.invalidateQueries({ queryKey: queryKeys.history.all() })
    }
    wasRunning.current = isRunning ?? false
  }, [isRunning, queryClient])
}
