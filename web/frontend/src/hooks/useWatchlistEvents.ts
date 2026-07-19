import { useMemo } from 'react'
import type { ActivityEvent } from '@/api/types'
import { useEvents } from './useEvents'
import { useInfo } from './useInfo'

/**
 * Returns all activity events where payload.watchlist matches the given name,
 * newest-first. Polls at 2s during an active run, 15s otherwise.
 */
export function useWatchlistEvents(name: string): {
  events: ActivityEvent[]
  isLoading: boolean
  isError: boolean
  error: Error | null
} {
  const { data: info } = useInfo()
  const eventsQuery = useEvents(info?.run_in_progress ?? false)

  const events = useMemo(
    () =>
      (eventsQuery.data?.events ?? []).filter(
        (e) => typeof e.payload.watchlist === 'string' && e.payload.watchlist === name,
      ),
    [eventsQuery.data, name],
  )

  return {
    events,
    isLoading: eventsQuery.isLoading,
    isError: eventsQuery.isError,
    error: eventsQuery.error,
  }
}
