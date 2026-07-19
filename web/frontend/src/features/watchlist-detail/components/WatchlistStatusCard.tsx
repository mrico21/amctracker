import { AlertTriangle, Bell, CheckCircle, Clock, HelpCircle, Shield, XCircle } from 'lucide-react'
import type { CurrentAvailability, WatchlistHealth, WatchlistHealthStatus } from '@/types/view-models'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { formatRelativeTime } from '@/lib/format'
import { cn } from '@/lib/utils'

// ── Health status display ─────────────────────────────────────────────────────

interface HealthBadgeProps {
  status: WatchlistHealthStatus
  consecutiveBlocks: number
}

function HealthBadge({ status, consecutiveBlocks }: HealthBadgeProps) {
  const configs = {
    healthy: {
      icon: <CheckCircle className="h-4 w-4" />,
      label: 'Healthy',
      className: 'text-emerald-700 dark:text-emerald-400',
      dotClass: 'bg-emerald-500',
    },
    blocked: {
      icon: <Shield className="h-4 w-4" />,
      label: consecutiveBlocks > 1 ? `Blocked (${consecutiveBlocks} consecutive)` : 'Blocked',
      className: 'text-amber-700 dark:text-amber-400',
      dotClass: 'bg-amber-500',
    },
    failed: {
      icon: <XCircle className="h-4 w-4" />,
      label: 'Failed',
      className: 'text-red-600 dark:text-red-400',
      dotClass: 'bg-red-500',
    },
    unknown: {
      icon: <HelpCircle className="h-4 w-4" />,
      label: 'Not yet run',
      className: 'text-muted-foreground',
      dotClass: 'bg-muted-foreground',
    },
  } satisfies Record<WatchlistHealthStatus, object>

  const cfg = configs[status]

  return (
    <div className={cn('flex items-center gap-2 font-semibold', cfg.className)}>
      {cfg.icon}
      <span className="text-base">{cfg.label}</span>
    </div>
  )
}

// ── Stat cell ─────────────────────────────────────────────────────────────────

function StatCell({
  icon,
  label,
  value,
  valueClassName,
}: {
  icon: React.ReactNode
  label: string
  value: string
  valueClassName?: string
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        <span className="text-muted-foreground">{icon}</span>
        {label}
      </div>
      <p className={cn('text-sm font-medium text-foreground', valueClassName)}>{value}</p>
    </div>
  )
}

// ── Availability display ──────────────────────────────────────────────────────

function AvailabilityRow({ availability }: { availability: CurrentAvailability | null }) {
  if (!availability) {
    return (
      <p className="text-xs text-muted-foreground">
        Availability not yet known — run the tracker to check.
      </p>
    )
  }

  const { seatsAvailable, windowsAvailable, availableSeats, availableWindows, asOf } = availability
  const hasAnything = seatsAvailable > 0 || windowsAvailable > 0

  if (!hasAnything) {
    return (
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">No target seats currently available</p>
        {asOf && (
          <p className="text-xs text-muted-foreground">as of {formatRelativeTime(asOf)}</p>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-1.5">
      {seatsAvailable > 0 && (
        <div>
          <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
            {seatsAvailable} seat{seatsAvailable !== 1 ? 's' : ''} available
          </p>
          {availableSeats.length > 0 && (
            <p className="text-xs text-emerald-600 dark:text-emerald-500">
              {availableSeats.join(', ')}
            </p>
          )}
        </div>
      )}
      {windowsAvailable > 0 && (
        <div>
          <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
            {windowsAvailable} adjacent window{windowsAvailable !== 1 ? 's' : ''} available
          </p>
          {availableWindows.length > 0 && (
            <p className="text-xs text-emerald-600 dark:text-emerald-500">
              {availableWindows.join(', ')}
            </p>
          )}
        </div>
      )}
      {asOf && (
        <p className="text-xs text-muted-foreground">as of {formatRelativeTime(asOf)}</p>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

interface WatchlistStatusCardProps {
  health: WatchlistHealth
  availability: CurrentAvailability | null
  isLoading?: boolean
}

export function WatchlistStatusCard({
  health,
  availability,
  isLoading = false,
}: WatchlistStatusCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-4 space-y-4">
          <Skeleton className="h-6 w-28" />
          <div className="grid grid-cols-3 gap-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
          <Skeleton className="h-4 w-2/3" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent className="p-4 space-y-4">
        {/* Health status */}
        <HealthBadge status={health.status} consecutiveBlocks={health.consecutiveBlocks} />

        {/* Three stat cells */}
        <div className="grid grid-cols-3 gap-4">
          <StatCell
            icon={<Clock className="h-3 w-3" />}
            label="Last Checked"
            value={formatRelativeTime(health.lastChecked)}
          />
          <StatCell
            icon={<CheckCircle className="h-3 w-3" />}
            label="Last Success"
            value={formatRelativeTime(health.lastSuccess)}
            valueClassName={
              health.lastSuccess == null ? 'text-muted-foreground' : undefined
            }
          />
          <StatCell
            icon={<Bell className="h-3 w-3" />}
            label="Last Notification"
            value={formatRelativeTime(health.lastNotification)}
            valueClassName={
              health.lastNotification == null ? 'text-muted-foreground' : undefined
            }
          />
        </div>

        {/* Divider */}
        <div className="border-t" />

        {/* Availability */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            <AlertTriangle className="h-3 w-3" />
            Current Availability
          </div>
          <AvailabilityRow availability={availability} />
        </div>
      </CardContent>
    </Card>
  )
}
