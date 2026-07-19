import { useMemo } from 'react'
import type { ActivityEvent } from '@/api/types'
import { useEvents } from './useEvents'

/**
 * Returns all activity events where payload.watchlist matches the given name,
 * newest-first. Polls at the standard resting rate (15s).
 */
export function useWatchlistEvents(name: string): {
  events: ActivityEvent[]
  isLoading: boolean
  isError: boolean
  error: Error | null
} {
  const eventsQuery = useEvents(false)

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
