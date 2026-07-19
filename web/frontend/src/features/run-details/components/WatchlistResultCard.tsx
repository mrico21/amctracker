import { ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { ActivityEvent, WatchlistRunResult } from '@/api/types'
import { MonitoringConfig } from '@/components/common/MonitoringConfig'
import { NotificationDetail } from '@/components/common/NotificationDetail'
import { StatusBadge } from '@/components/common/StatusBadge'
import { StatusIcon } from '@/components/common/StatusIcon'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { deriveNotificationSummary } from '@/lib/activity'
import { cn } from '@/lib/utils'

// ── Availability summary ──────────────────────────────────────────────────────

function AvailabilityRow({ result }: { result: WatchlistRunResult }) {
  const hasSeats = result.seats_available > 0
  const hasAdjacent = result.adjacent_windows_available > 0

  if (!hasSeats && !hasAdjacent) return null

  return (
    <div className="flex flex-wrap items-center gap-3">
      {hasSeats && (
        <span className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
          {result.seats_available} seat{result.seats_available !== 1 ? 's' : ''} available
        </span>
      )}
      {hasAdjacent && (
        <span className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
          {result.adjacent_windows_available} adjacent window
          {result.adjacent_windows_available !== 1 ? 's' : ''}
        </span>
      )}
    </div>
  )
}

// ── Main card ─────────────────────────────────────────────────────────────────

interface WatchlistResultCardProps {
  result: WatchlistRunResult
  /** Activity events belonging to this watchlist in this run */
  events?: ActivityEvent[]
  /** UUID for linking the watchlist name to its detail page */
  watchlistId?: string
}

export function WatchlistResultCard({
  result,
  events = [],
  watchlistId,
}: WatchlistResultCardProps) {
  const isDisabled = !result.enabled
  const isFailed = result.status === 'failed'

  // Derive notification summaries from structured events first, then fall back
  // to the boolean flag from the run result for older history files
  const notifEvents = events.filter((e) => e.event_type === 'notification_sent')
  const notifSummaries = notifEvents.map(deriveNotificationSummary)
  const showFallbackNotif = notifSummaries.length === 0 && result.notification_sent

  return (
    <Card className={cn(isDisabled && 'opacity-60')}>
      <CardContent className="p-4">
        <div className="space-y-3">
          {/* Header row */}
          <div className="flex items-start gap-2.5">
            <StatusIcon status={result.status} className="mt-0.5 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                {/* Name links to watchlist detail when id is available */}
                {watchlistId ? (
                  <Link
                    to={`/watchlists/${watchlistId}`}
                    className="font-medium text-foreground hover:underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {result.name}
                  </Link>
                ) : (
                  <span className="font-medium text-foreground">{result.name}</span>
                )}
                {isDisabled && (
                  <Badge variant="outline" className="text-xs">
                    Disabled
                  </Badge>
                )}
              </div>
            </div>
            <div className="flex flex-shrink-0 items-center gap-2">
              <StatusBadge status={result.status} />
              <a
                href={result.showtime_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground/50 transition-colors hover:text-muted-foreground"
                title="Open showtime page"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>

          {/* Body — only for non-disabled watchlists */}
          {!isDisabled && (
            <div className="ml-6 space-y-3">
              {/* Seat availability count */}
              <AvailabilityRow result={result} />

              {/* Notification detail from events (structured) */}
              {notifSummaries.length > 0 && (
                <NotificationDetail summaries={notifSummaries} />
              )}

              {/* Fallback: boolean flag from older run results without event data */}
              {showFallbackNotif && (
                <NotificationDetail
                  summaries={[
                    {
                      notificationType: null,
                      seats: [],
                      change: null,
                      windowSize: null,
                      timestamp: '',
                      message: 'Notification sent (details not available for this run)',
                    },
                  ]}
                />
              )}

              {/* Monitoring configuration */}
              <MonitoringConfig
                watch_seats={result.monitoring.watch_seats}
                watch_any={result.monitoring.watch_any}
                watch_adjacent={result.monitoring.watch_adjacent}
                showLabel
              />

              {/* Failure detail */}
              {isFailed && result.error_message && (
                <div className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2.5">
                  <p className="text-xs font-medium text-destructive">
                    {result.failure_type ?? 'Error'}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{result.error_message}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
