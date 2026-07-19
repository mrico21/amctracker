import { useMemo } from 'react'
import type { ActivityEvent } from '@/api/types'
import { groupEventsByWatchlist } from '@/lib/activity'
import { useEvents } from './useEvents'
import { useInfo } from './useInfo'

/**
 * Returns activity events belonging to a specific run, grouped by watchlist name.
 * Polls at 2s during an active run, 15s otherwise.
 */
export function useRunEvents(runId: string | null | undefined): {
  events: ActivityEvent[]
  byWatchlist: Map<string, ActivityEvent[]>
  isLoading: boolean
} {
  const { data: info } = useInfo()
  const eventsQuery = useEvents(info?.run_in_progress ?? false)

  const events = useMemo(
    () =>
      !runId
        ? []
        : (eventsQuery.data?.events ?? []).filter((e) => e.run_id === runId),
    [eventsQuery.data, runId],
  )

  const byWatchlist = useMemo(() => groupEventsByWatchlist(events), [events])

  return { events, byWatchlist, isLoading: eventsQuery.isLoading }
}
