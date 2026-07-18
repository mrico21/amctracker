import { Calendar, Clock, Moon } from 'lucide-react'
import type { SchedulerStatus } from '@/api/types'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { formatRelativeTime } from '@/lib/format'
import { cn } from '@/lib/utils'

interface SchedulerCardProps {
  scheduler: SchedulerStatus | undefined
  isLoading: boolean
}

function formatCountdown(seconds: number | null): string {
  if (seconds === null) return '—'
  if (seconds <= 0) return 'Now'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  if (m === 0) return `${s}s`
  return `${m}m ${s}s`
}

function formatNextRun(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

function formatIntervalRange(minSec: number, maxSec: number): string {
  const fmt = (s: number) => {
    if (s < 60) return `${s}s`
    const m = Math.round(s / 60)
    return `${m}m`
  }
  if (minSec === maxSec) return `every ${fmt(minSec)}`
  return `every ${fmt(minSec)}–${fmt(maxSec)}`
}

function StatusBadgeScheduler({ status }: { status: SchedulerStatus['status'] }) {
  if (status === 'disabled') {
    return <Badge variant="secondary">Disabled</Badge>
  }
  if (status === 'quiet') {
    return (
      <Badge variant="outline" className="border-amber-400 text-amber-600 dark:text-amber-400">
        <Moon className="mr-1 h-3 w-3" />
        Quiet Hours
      </Badge>
    )
  }
  return (
    <Badge variant="outline" className="border-emerald-400 text-emerald-600 dark:text-emerald-400">
      <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
      Scheduled
    </Badge>
  )
}

export function SchedulerCard({ scheduler, isLoading }: SchedulerCardProps) {
  const isDisabled = !scheduler || scheduler.status === 'disabled'

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              Scheduler
            </CardTitle>
            {scheduler && !isLoading && (
              <span className="text-xs text-muted-foreground">
                {formatIntervalRange(scheduler.min_interval_seconds, scheduler.max_interval_seconds)}
              </span>
            )}
          </div>
          {scheduler && <StatusBadgeScheduler status={scheduler.status} />}
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {isLoading ? (
          <div className="grid grid-cols-3 gap-4">
            {[0, 1, 2].map((i) => (
              <div key={i} className="space-y-1.5">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-5 w-12" />
              </div>
            ))}
          </div>
        ) : !scheduler ? (
          <p className="text-sm text-muted-foreground">Scheduler unavailable</p>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            <Stat
              label="Last Run"
              value={formatRelativeTime(scheduler.last_triggered_at)}
              sub={scheduler.last_trigger_type ?? undefined}
            />
            <Stat
              label="Next Run"
              value={isDisabled ? '—' : formatNextRun(scheduler.next_run_at)}
              sub={
                scheduler.status === 'quiet' && scheduler.quiet_hours_start && scheduler.quiet_hours_end
                  ? `quiet ${scheduler.quiet_hours_start}–${scheduler.quiet_hours_end}`
                  : undefined
              }
              subClassName={scheduler.status === 'quiet' ? 'text-amber-600 dark:text-amber-500' : undefined}
            />
            <Stat
              label="Countdown"
              value={isDisabled ? '—' : formatCountdown(scheduler.countdown_seconds)}
              valueClassName={
                !isDisabled && scheduler.countdown_seconds !== null && scheduler.countdown_seconds < 60
                  ? 'text-amber-600 dark:text-amber-400'
                  : undefined
              }
              icon={
                scheduler.status === 'scheduled' ? (
                  <Clock className="h-3.5 w-3.5 text-muted-foreground animate-pulse" />
                ) : undefined
              }
            />
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function Stat({
  label,
  value,
  sub,
  subClassName,
  valueClassName,
  icon,
}: {
  label: string
  value: string
  sub?: string
  subClassName?: string
  valueClassName?: string
  icon?: React.ReactNode
}) {
  return (
    <div className="space-y-0.5">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <div className="flex items-center gap-1">
        <p className={cn('text-sm font-semibold text-foreground', valueClassName)}>{value}</p>
        {icon}
      </div>
      {sub && <p className={cn('text-xs text-muted-foreground capitalize', subClassName)}>{sub}</p>}
    </div>
  )
}
