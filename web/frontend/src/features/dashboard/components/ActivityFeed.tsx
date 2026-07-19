import {
  ActivityIcon,
  AlertTriangle,
  Bell,
  Calendar,
  CalendarClock,
  CheckCircle,
  CircleDashed,
  Play,
  SkipForward,
  XCircle,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import type { ActivityEvent, ActivityEventType } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useWatchlists } from '@/hooks/useWatchlists'
import { truncateUuid } from '@/lib/format'
import { cn } from '@/lib/utils'

// ── Low-signal events hidden in "Highlights" mode ────────────────────────────

const LOW_SIGNAL_TYPES: ActivityEventType[] = ['watchlist_start', 'watchlist_complete', 'scheduler_skipped']

// ── Event appearance ──────────────────────────────────────────────────────────

type EventStyle = { icon: React.ReactNode; color: string; muted: boolean }

function eventStyle(type: ActivityEventType): EventStyle {
  switch (type) {
    case 'run_start':
      return { icon: <Play className="h-3.5 w-3.5" />, color: 'text-blue-600 dark:text-blue-400', muted: false }
    case 'run_complete':
      return { icon: <CheckCircle className="h-3.5 w-3.5" />, color: 'text-emerald-600 dark:text-emerald-400', muted: false }
    case 'run_cancelled':
      return { icon: <XCircle className="h-3.5 w-3.5" />, color: 'text-red-500 dark:text-red-400', muted: false }
    case 'watchlist_start':
      return { icon: <CircleDashed className="h-3.5 w-3.5" />, color: 'text-muted-foreground', muted: true }
    case 'watchlist_complete':
      return { icon: <CheckCircle className="h-3.5 w-3.5" />, color: 'text-muted-foreground', muted: true }
    case 'watchlist_blocked':
      return { icon: <AlertTriangle className="h-3.5 w-3.5" />, color: 'text-amber-600 dark:text-amber-400', muted: false }
    case 'watchlist_failed':
      return { icon: <XCircle className="h-3.5 w-3.5" />, color: 'text-red-500 dark:text-red-400', muted: false }
    case 'notification_sent':
      return { icon: <Bell className="h-3.5 w-3.5" />, color: 'text-emerald-600 dark:text-emerald-400', muted: false }
    case 'scheduler_triggered':
      return { icon: <Calendar className="h-3.5 w-3.5" />, color: 'text-blue-500 dark:text-blue-400', muted: false }
    case 'scheduler_skipped':
      return { icon: <SkipForward className="h-3.5 w-3.5" />, color: 'text-muted-foreground', muted: true }
    default:
      return { icon: <CalendarClock className="h-3.5 w-3.5" />, color: 'text-muted-foreground', muted: true }
  }
}

// ── Time / date formatting ────────────────────────────────────────────────────

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
  const sameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
  if (sameDay(d, today)) return 'Today'
  if (sameDay(d, yesterday)) return 'Yesterday'
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function dayKey(iso: string): string {
  const d = new Date(iso)
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}

// ── Single event row ──────────────────────────────────────────────────────────

function EventRow({
  event,
  watchlistIdByName,
}: {
  event: ActivityEvent
  watchlistIdByName: Map<string, string>
}) {
  const navigate = useNavigate()
  const { icon, color, muted } = eventStyle(event.event_type)

  const watchlistName =
    typeof event.payload.watchlist === 'string' ? event.payload.watchlist : null
  const watchlistId = watchlistName ? watchlistIdByName.get(watchlistName) : undefined
  const hasRun = !!event.run_id

  function handleRowClick() {
    if (hasRun) void navigate(`/history/${event.run_id}`)
  }

  return (
    <div
      className={cn(
        'py-2 first:pt-0',
        muted && 'opacity-60',
        hasRun && 'cursor-pointer rounded-sm hover:bg-accent/40 transition-colors px-1 -mx-1',
      )}
      onClick={hasRun ? handleRowClick : undefined}
    >
      {/* Primary row */}
      <div className="flex items-start gap-3">
        <span className={cn('mt-0.5 flex-shrink-0', color)}>{icon}</span>
        <p className="min-w-0 flex-1 text-sm leading-snug text-foreground">{event.message}</p>
        <p className="flex-shrink-0 text-xs text-muted-foreground tabular-nums">
          {formatTime(event.timestamp)}
        </p>
      </div>

      {/* Navigation chips — watchlist link and/or run link */}
      {(watchlistId || hasRun) && (
        <div
          className="ml-6 mt-1 flex flex-wrap items-center gap-2"
          onClick={(e) => e.stopPropagation()}
        >
          {watchlistId && (
            <Link
              to={`/watchlists/${watchlistId}`}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors underline-offset-2 hover:underline"
            >
              {watchlistName}
            </Link>
          )}
          {hasRun && (
            <Link
              to={`/history/${event.run_id!}`}
              className="font-mono text-xs text-muted-foreground/60 hover:text-muted-foreground transition-colors"
              title={`View run ${event.run_id}`}
            >
              {truncateUuid(event.run_id!)}
            </Link>
          )}
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

interface ActivityFeedProps {
  events: ActivityEvent[] | undefined
  isLoading: boolean
}

export function ActivityFeed({ events, isLoading }: ActivityFeedProps) {
  const [showAll, setShowAll] = useState(false)
  const watchlistsQuery = useWatchlists()

  // Build name → id map for navigation chips
  const watchlistIdByName = useMemo(() => {
    const map = new Map<string, string>()
    for (const w of watchlistsQuery.data ?? []) map.set(w.name, w.id)
    return map
  }, [watchlistsQuery.data])

  const allEvents = events ?? []
  const displayed = showAll
    ? allEvents
    : allEvents.filter((e) => !LOW_SIGNAL_TYPES.includes(e.event_type))

  const hiddenCount = allEvents.length - displayed.length
  const totalCount = allEvents.length

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
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <ActivityIcon className="h-4 w-4 text-muted-foreground" />
            Activity
            {totalCount > 0 && (
              <Badge variant="secondary" className="px-1.5 py-0 text-xs font-normal">
                {totalCount}
              </Badge>
            )}
          </CardTitle>
          {(hiddenCount > 0 || showAll) && (
            <button
              onClick={() => setShowAll((v) => !v)}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {showAll ? 'Highlights' : `All (+${hiddenCount})`}
            </button>
          )}
        </div>
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
            {totalCount > 0
              ? 'No highlights yet — click All to see all events'
              : 'No activity yet'}
          </p>
        ) : (
          <div>
            {rows.map((row, i) =>
              row.type === 'separator' ? (
                <DateDivider key={`sep-${i}`} label={row.label} />
              ) : (
                <div key={row.event.id} className="border-b last:border-b-0">
                  <EventRow event={row.event} watchlistIdByName={watchlistIdByName} />
                </div>
              ),
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
