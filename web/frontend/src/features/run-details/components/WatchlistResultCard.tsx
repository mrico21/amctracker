import { Bell, ExternalLink } from 'lucide-react'
import type { WatchlistAdjacentConfig, WatchlistRunMonitoring, WatchlistRunResult } from '@/api/types'
import { StatusBadge } from '@/components/common/StatusBadge'
import { StatusIcon } from '@/components/common/StatusIcon'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

// ── Monitoring config display ─────────────────────────────────────────────────

function SeatBadge({ label }: { label: string }) {
  return (
    <Badge variant="secondary" className="font-mono text-xs">
      {label}
    </Badge>
  )
}

function AdjacentRow({ cfg }: { cfg: WatchlistAdjacentConfig }) {
  return (
    <div className="flex flex-wrap items-center gap-1">
      <span className="text-xs text-muted-foreground">
        Adjacent {cfg.count} in:
      </span>
      {cfg.rows.map((row) => (
        <SeatBadge key={row} label={`Row ${row}`} />
      ))}
    </div>
  )
}

function MonitoringConfig({ monitoring }: { monitoring: WatchlistRunMonitoring }) {
  const hasSeats = monitoring.watch_seats.length > 0
  const hasAny = monitoring.watch_any.length > 0
  const hasAdjacent = monitoring.watch_adjacent.length > 0

  if (!hasSeats && !hasAny && !hasAdjacent) return null

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Monitoring
      </p>
      <div className="space-y-1.5">
        {hasSeats && (
          <div className="flex flex-wrap items-center gap-1">
            <span className="text-xs text-muted-foreground">Specific seats:</span>
            {monitoring.watch_seats.map((seat) => (
              <SeatBadge key={seat} label={seat} />
            ))}
          </div>
        )}
        {hasAny && (
          <div className="flex flex-wrap items-center gap-1">
            <span className="text-xs text-muted-foreground">Any seat in:</span>
            {monitoring.watch_any.map((row) => (
              <SeatBadge key={row} label={`Row ${row}`} />
            ))}
          </div>
        )}
        {hasAdjacent &&
          monitoring.watch_adjacent.map((cfg, i) => (
            <AdjacentRow key={i} cfg={cfg} />
          ))}
      </div>
    </div>
  )
}

// ── Seat availability display ─────────────────────────────────────────────────

function SeatAvailability({ result }: { result: WatchlistRunResult }) {
  const hasSeats = result.seats_available > 0
  const hasAdjacent = result.adjacent_windows_available > 0

  if (!hasSeats && !hasAdjacent && !result.notification_sent) return null

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
      {result.notification_sent && (
        <span className="flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
          <Bell className="h-3 w-3" />
          Notified
        </span>
      )}
    </div>
  )
}

// ── Main card ─────────────────────────────────────────────────────────────────

interface WatchlistResultCardProps {
  result: WatchlistRunResult
}

export function WatchlistResultCard({ result }: WatchlistResultCardProps) {
  const isDisabled = !result.enabled
  const isFailed = result.status === 'failed'

  return (
    <Card className={cn(isDisabled && 'opacity-60')}>
      <CardContent className="p-4">
        <div className="space-y-3">
          {/* Header row: icon · name · [Disabled badge] · status · external link */}
          <div className="flex items-start gap-2.5">
            <StatusIcon
              status={result.status}
              className="mt-0.5 flex-shrink-0"
            />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-foreground">{result.name}</span>
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

          {/* Body: only for active (non-disabled) watchlists */}
          {!isDisabled && (
            <div className="ml-6 space-y-3">
              {/* Seat availability + notification */}
              <SeatAvailability result={result} />

              {/* Monitoring configuration */}
              <MonitoringConfig monitoring={result.monitoring} />

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
