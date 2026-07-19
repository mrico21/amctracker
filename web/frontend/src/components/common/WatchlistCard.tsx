import { Bell, ExternalLink, Eye, EyeOff } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { WatchlistEntry, WatchlistRunResult } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { MonitoringConfig } from './MonitoringConfig'
import { StatusBadge } from './StatusBadge'

interface WatchlistCardProps {
  watchlist: WatchlistEntry
  latestResult?: WatchlistRunResult
}

export function WatchlistCard({ watchlist, latestResult }: WatchlistCardProps) {
  const isEnabled = watchlist.enabled
  const seatsAvailable = latestResult?.seats_available ?? 0
  const adjacentAvailable = latestResult?.adjacent_windows_available ?? 0
  const hasAvailability = seatsAvailable > 0 || adjacentAvailable > 0
  const showLastRunStatus = isEnabled && latestResult != null

  return (
    <Link
      to={`/watchlists/${watchlist.id}`}
      className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-xl"
    >
      <Card className={`transition-colors hover:border-border/80 hover:bg-accent/30 ${!isEnabled ? 'opacity-60' : ''}`}>
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
                {showLastRunStatus && <StatusBadge status={latestResult!.status} />}
                {/* Stop propagation so the Link doesn't trigger when clicking AMC */}
                <a
                  href={watchlist.showtime_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="text-muted-foreground/50 transition-colors hover:text-muted-foreground"
                  title="Open showtime on AMC"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
            </div>

            {/* Body */}
            <div className="ml-6 space-y-2.5">
              <MonitoringConfig
                watch_seats={watchlist.watch_seats}
                watch_any={watchlist.watch_any}
                watch_adjacent={watchlist.watch_adjacent}
              />

              {/* Availability summary from latest run */}
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
    </Link>
  )
}
