import type { ActivityEvent } from '@/api/types'
import type {
  CurrentAvailability,
  NotificationSummary,
  NotificationType,
  WatchlistHealth,
} from '@/types/view-models'

// Event types that represent a definitive check outcome
const OUTCOME_TYPES = new Set(['watchlist_complete', 'watchlist_blocked', 'watchlist_failed'])

// ── WatchlistHealth ───────────────────────────────────────────────────────────

/**
 * Derives health summary for a single watchlist from its activity events
 * (newest-first order expected).
 */
export function deriveWatchlistHealth(events: ActivityEvent[]): WatchlistHealth {
  let status: WatchlistHealth['status'] = 'unknown'
  let lastChecked: string | null = null
  let lastSuccess: string | null = null
  let lastNotification: string | null = null
  let consecutiveBlocks = 0
  let countingBlocks = true

  for (const event of events) {
    if (OUTCOME_TYPES.has(event.event_type)) {
      if (lastChecked === null) {
        lastChecked = event.timestamp
        if (event.event_type === 'watchlist_complete') status = 'healthy'
        else if (event.event_type === 'watchlist_blocked') status = 'blocked'
        else if (event.event_type === 'watchlist_failed') status = 'failed'
      }
      if (event.event_type === 'watchlist_complete' && lastSuccess === null) {
        lastSuccess = event.timestamp
      }
      if (countingBlocks) {
        if (event.event_type === 'watchlist_blocked') {
          consecutiveBlocks++
        } else {
          countingBlocks = false
        }
      }
    }
    if (event.event_type === 'notification_sent' && lastNotification === null) {
      lastNotification = event.timestamp
    }
  }

  return { status, lastChecked, lastSuccess, lastNotification, consecutiveBlocks }
}

// ── CurrentAvailability ───────────────────────────────────────────────────────

/**
 * Reads seat availability from the most recent watchlist_complete event.
 * Returns null if no such event exists.
 */
export function deriveCurrentAvailability(events: ActivityEvent[]): CurrentAvailability | null {
  for (const event of events) {
    if (event.event_type !== 'watchlist_complete') continue
    const p = event.payload

    const seatsAvailable = typeof p.seats_available === 'number' ? p.seats_available : 0
    const windowsAvailable = typeof p.adj_available === 'number' ? p.adj_available : 0
    const availableSeats = Array.isArray(p.available_seats)
      ? (p.available_seats as unknown[]).filter((s): s is string => typeof s === 'string')
      : []
    const availableWindows = Array.isArray(p.available_windows)
      ? (p.available_windows as unknown[]).filter((s): s is string => typeof s === 'string')
      : []

    return { seatsAvailable, windowsAvailable, availableSeats, availableWindows, asOf: event.timestamp }
  }
  return null
}

// ── NotificationSummary ───────────────────────────────────────────────────────

const VALID_NOTIFICATION_TYPES = new Set<NotificationType>([
  'watch_seats',
  'watch_any',
  'watch_adjacent',
])

/**
 * Derives structured notification context from a notification_sent event.
 * Gracefully handles missing/partial payloads from older event schema versions.
 *
 * Rendering priority:
 *   1. Structured payload (notificationType + seats + optional change/windowSize)
 *   2. message field (event-level human-readable string)
 *   3. Generic "Notification sent" (neither available)
 */
export function deriveNotificationSummary(event: ActivityEvent): NotificationSummary {
  const p = event.payload

  const rawType = p.notification_type
  const notificationType: NotificationType | null =
    typeof rawType === 'string' && VALID_NOTIFICATION_TYPES.has(rawType as NotificationType)
      ? (rawType as NotificationType)
      : null

  const seats = Array.isArray(p.seats)
    ? (p.seats as unknown[]).filter((s): s is string => typeof s === 'string')
    : []

  const change = typeof p.change === 'string' ? p.change : null
  const windowSize = typeof p.window_size === 'number' ? p.window_size : null

  return {
    notificationType,
    seats,
    change,
    windowSize,
    timestamp: event.timestamp,
    message: event.message,
  }
}

// ── Grouping helpers ──────────────────────────────────────────────────────────

/**
 * Groups events by payload.watchlist name. Events without a watchlist name
 * are ignored. Returns a Map so insertion order is preserved.
 */
export function groupEventsByWatchlist(events: ActivityEvent[]): Map<string, ActivityEvent[]> {
  const map = new Map<string, ActivityEvent[]>()
  for (const event of events) {
    const name = typeof event.payload.watchlist === 'string' ? event.payload.watchlist : null
    if (!name) continue
    const bucket = map.get(name) ?? []
    bucket.push(event)
    map.set(name, bucket)
  }
  return map
}
