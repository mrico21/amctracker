import { ExternalLink } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { ActivityEvent } from '@/api/types'
import { EventDateDivider } from '@/components/common/EventDateDivider'
import { NotificationDetail } from '@/components/common/NotificationDetail'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { deriveNotificationSummary } from '@/lib/activity'
import { getEventStyle } from '@/lib/event-style'
import { dayKey, formatDateLabel, formatTime } from '@/lib/format'
import { cn } from '@/lib/utils'

// ── Event row ─────────────────────────────────────────────────────────────────

function EventRow({ event, navigate }: { event: ActivityEvent; navigate: ReturnType<typeof useNavigate> }) {
  const { icon, color } = getEventStyle(event.event_type)
  const isNotification = event.event_type === 'notification_sent'
  const hasRun = !!event.run_id

  return (
    <div
      className={cn(
        'space-y-1.5 py-2.5',
        hasRun && 'cursor-pointer rounded-md px-2 -mx-2 hover:bg-accent/50 transition-colors',
      )}
      onClick={hasRun ? () => void navigate(`/history/${event.run_id}`) : undefined}
    >
      <div className="flex items-start gap-3">
        <span className={cn('mt-0.5 flex-shrink-0', color)}>{icon}</span>
        <p className="min-w-0 flex-1 text-sm leading-snug text-foreground">{event.message}</p>
        <div className="flex flex-shrink-0 items-center gap-1.5">
          {hasRun && (
            <ExternalLink className="h-3 w-3 text-muted-foreground/50" aria-label="View run" />
          )}
          <p className="text-xs text-muted-foreground tabular-nums">{formatTime(event.timestamp)}</p>
        </div>
      </div>

      {/* Notification detail inline */}
      {isNotification && (
        <div className="ml-6">
          <NotificationDetail summaries={[deriveNotificationSummary(event)]} />
        </div>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

interface WatchlistActivityTimelineProps {
  events: ActivityEvent[]
  isLoading: boolean
  maxEvents?: number
}

export function WatchlistActivityTimeline({
  events,
  isLoading,
  maxEvents = 20,
}: WatchlistActivityTimelineProps) {
  const navigate = useNavigate()
  const displayed = events.slice(0, maxEvents)

  // Build rows with date separators
  type Row =
    | { type: 'separator'; label: string }
    | { type: 'event'; event: ActivityEvent }

  const rows: Row[] = []
  let lastDay: string | null = null
  for (const event of displayed) {
    const key = dayKey(event.timestamp)
    if (key !== lastDay) {
      rows.push({ type: 'separator', label: formatDateLabel(event.timestamp) })
      lastDay = key
    }
    rows.push({ type: 'event', event })
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Recent Activity</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        {isLoading ? (
          <div className="space-y-3">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <Skeleton className="h-4 w-4 rounded-full flex-shrink-0" />
                <Skeleton className="h-3.5 flex-1" />
                <Skeleton className="h-3 w-16 flex-shrink-0" />
              </div>
            ))}
          </div>
        ) : displayed.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-foreground">
            No activity recorded for this watchlist yet
          </p>
        ) : (
          <div>
            {rows.map((row, i) =>
              row.type === 'separator' ? (
                <EventDateDivider key={`sep-${i}`} label={row.label} />
              ) : (
                <div key={row.event.id} className="border-b last:border-b-0">
                  <EventRow event={row.event} navigate={navigate} />
                </div>
              ),
            )}
            {events.length > maxEvents && (
              <p className="pt-3 text-center text-xs text-muted-foreground">
                Showing {maxEvents} of {events.length} events
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
