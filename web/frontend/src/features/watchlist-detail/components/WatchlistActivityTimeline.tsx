import {
  AlertTriangle,
  Bell,
  Calendar,
  CheckCircle,
  CircleDashed,
  ExternalLink,
  Play,
  SkipForward,
  XCircle,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { ActivityEvent, ActivityEventType } from '@/api/types'
import { NotificationDetail } from '@/components/common/NotificationDetail'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { deriveNotificationSummary } from '@/lib/activity'
import { cn } from '@/lib/utils'

// ── Event appearance ──────────────────────────────────────────────────────────

function eventIcon(type: ActivityEventType): React.ReactNode {
  switch (type) {
    case 'run_start': return <Play className="h-3.5 w-3.5" />
    case 'run_complete': return <CheckCircle className="h-3.5 w-3.5" />
    case 'run_cancelled': return <XCircle className="h-3.5 w-3.5" />
    case 'watchlist_start': return <CircleDashed className="h-3.5 w-3.5" />
    case 'watchlist_complete': return <CheckCircle className="h-3.5 w-3.5" />
    case 'watchlist_blocked': return <AlertTriangle className="h-3.5 w-3.5" />
    case 'watchlist_failed': return <XCircle className="h-3.5 w-3.5" />
    case 'notification_sent': return <Bell className="h-3.5 w-3.5" />
    case 'scheduler_triggered': return <Calendar className="h-3.5 w-3.5" />
    case 'scheduler_skipped': return <SkipForward className="h-3.5 w-3.5" />
    default: return <CircleDashed className="h-3.5 w-3.5" />
  }
}

function iconColor(type: ActivityEventType): string {
  switch (type) {
    case 'notification_sent':
    case 'run_complete':
    case 'watchlist_complete':
      return 'text-emerald-600 dark:text-emerald-400'
    case 'watchlist_blocked':
      return 'text-amber-600 dark:text-amber-400'
    case 'watchlist_failed':
    case 'run_cancelled':
      return 'text-red-500 dark:text-red-400'
    case 'run_start':
      return 'text-blue-600 dark:text-blue-400'
    default:
      return 'text-muted-foreground'
  }
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  })
}

function formatDateLabel(iso: string): string {
  const d = new Date(iso)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(today.getDate() - 1)
  const same = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
  if (same(d, today)) return 'Today'
  if (same(d, yesterday)) return 'Yesterday'
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function dayKey(iso: string): string {
  const d = new Date(iso)
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}

// ── Event row ─────────────────────────────────────────────────────────────────

function EventRow({ event }: { event: ActivityEvent }) {
  const navigate = useNavigate()
  const color = iconColor(event.event_type)
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
        <span className={cn('mt-0.5 flex-shrink-0', color)}>{eventIcon(event.event_type)}</span>
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

function DateDivider({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 py-1.5">
      <div className="h-px flex-1 bg-border" />
      <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </span>
      <div className="h-px flex-1 bg-border" />
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
                <DateDivider key={`sep-${i}`} label={row.label} />
              ) : (
                <div key={row.event.id} className="border-b last:border-b-0">
                  <EventRow event={row.event} />
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
