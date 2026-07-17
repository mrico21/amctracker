import { Bell, Eye, EyeOff, ExternalLink } from 'lucide-react'
import type { WatchlistAdjacentConfig, WatchlistEntry, WatchlistRunResult } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { StatusBadge } from './StatusBadge'

// ── Monitoring configuration detail ──────────────────────────────────────────

function SeatLabel({ label }: { label: string }) {
  return (
    <Badge variant="secondary" className="font-mono text-xs">
      {label}
    </Badge>
  )
}

function AdjacentRow({ cfg }: { cfg: WatchlistAdjacentConfig }) {
  return (
    <div className="flex flex-wrap items-center gap-1">
      <span className="text-xs text-muted-foreground">Adjacent {cfg.count} in:</span>
      {cfg.rows.map((row) => (
        <SeatLabel key={row} label={`Row ${row}`} />
      ))}
    </div>
  )
}

function MonitoringDetail({
  watch_seats,
  watch_any,
  watch_adjacent,
}: {
  watch_seats: string[]
  watch_any: string[]
  watch_adjacent: WatchlistAdjacentConfig[]
}) {
  const hasSeats = watch_seats.length > 0
  const hasAny = watch_any.length > 0
  const hasAdjacent = watch_adjacent.length > 0

  if (!hasSeats && !hasAny && !hasAdjacent) return null

  return (
    <div className="space-y-1.5">
      {hasSeats && (
        <div className="flex flex-wrap items-center gap-1">
          <span className="text-xs text-muted-foreground">Seats:</span>
          {watch_seats.map((seat) => (
            <SeatLabel key={seat} label={seat} />
          ))}
        </div>
      )}
      {hasAny && (
        <div className="flex flex-wrap items-center gap-1">
          <span className="text-xs text-muted-foreground">Any in:</span>
          {watch_any.map((row) => (
            <SeatLabel key={row} label={`Row ${row}`} />
          ))}
        </div>
      )}
      {hasAdjacent &&
        watch_adjacent.map((cfg, i) => <AdjacentRow key={i} cfg={cfg} />)}
    </div>
  )
}

// ── Main card ─────────────────────────────────────────────────────────────────

interface WatchlistCardProps {
  watchlist: WatchlistEntry
  /** Optional latest run result for this watchlist — shows availability summary */
  latestResult?: WatchlistRunResult
}

export function WatchlistCard({ watchlist, latestResult }: WatchlistCardProps) {
  const isEnabled = watchlist.enabled
  const seatsAvailable = latestResult?.seats_available ?? 0
  const adjacentAvailable = latestResult?.adjacent_windows_available ?? 0
  const hasAvailability = seatsAvailable > 0 || adjacentAvailable > 0
  const showLastRunStatus = isEnabled && latestResult != null

  return (
    <Card className={cn(!isEnabled && 'opacity-60')}>
      <CardContent className="p-4">
        <div className="space-y-3">
          {/* Header row */}
          <div className="flex items-start gap-2.5">
            {isEnabled ? (
              <Eye className="mt-0.5 h-4 w-4 flex-shrink-0 text-muted-foreground" />
            ) : (
              <EyeOff className="mt-0.5 h-4 w-4 flex-shrink-0 text-muted-foreground" />
            )}
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-foreground">{watchlist.name}</span>
                {!isEnabled && (
                  <Badge variant="outline" className="text-xs">
                    Disabled
                  </Badge>
                )}
              </div>
            </div>
            <div className="flex flex-shrink-0 items-center gap-2">
              {showLastRunStatus && (
                <StatusBadge status={latestResult!.status} />
              )}
              <a
                href={watchlist.showtime_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground/50 transition-colors hover:text-muted-foreground"
                title="Open showtime on AMC"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>

          {/* Body: monitoring config + availability */}
          <div className="ml-6 space-y-2.5">
            <MonitoringDetail
              watch_seats={watchlist.watch_seats}
              watch_any={watchlist.watch_any}
              watch_adjacent={watchlist.watch_adjacent}
            />

            {/* Latest run availability (enabled watchlists only) */}
            {isEnabled && latestResult && (hasAvailability || latestResult.notification_sent) && (
              <div className="flex flex-wrap items-center gap-3">
                {seatsAvailable > 0 && (
                  <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                    {seatsAvailable} seat{seatsAvailable !== 1 ? 's' : ''} available
                  </span>
                )}
                {adjacentAvailable > 0 && (
                  <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                    {adjacentAvailable} adjacent window{adjacentAvailable !== 1 ? 's' : ''}
                  </span>
                )}
                {latestResult.notification_sent && (
                  <span className="flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
                    <Bell className="h-3 w-3" />
                    Notified
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
