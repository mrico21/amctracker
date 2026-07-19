// ── Watchlist health ──────────────────────────────────────────────────────────

export type WatchlistHealthStatus = 'healthy' | 'blocked' | 'failed' | 'unknown'

export interface WatchlistHealth {
  status: WatchlistHealthStatus
  lastChecked: string | null
  lastSuccess: string | null
  lastNotification: string | null
  consecutiveBlocks: number
}

// ── Seat availability (derived from watchlist_complete event) ─────────────────

export interface CurrentAvailability {
  seatsAvailable: number
  windowsAvailable: number
  availableSeats: string[]
  availableWindows: string[]
  asOf: string | null
}

// ── Notification context (derived from notification_sent event) ───────────────

export type NotificationType = 'watch_seats' | 'watch_any' | 'watch_adjacent'

export interface NotificationSummary {
  notificationType: NotificationType | null
  seats: string[]
  change: string | null
  windowSize: number | null
  timestamp: string
  message: string
}
