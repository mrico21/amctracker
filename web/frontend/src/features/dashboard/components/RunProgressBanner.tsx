import { Bell, Loader2, ShieldAlert, X } from 'lucide-react'
import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { ActivityEvent, JobStatus } from '@/api/types'
import { queryKeys } from '@/lib/queryKeys'
import { cn } from '@/lib/utils'

interface RunProgressBannerProps {
  jobStatus: JobStatus | undefined
  events: ActivityEvent[]
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}m ${s}s`
}

export function RunProgressBanner({ jobStatus, events }: RunProgressBannerProps) {
  const queryClient = useQueryClient()
  const [cancelling, setCancelling] = useState(false)

  const status = jobStatus?.status ?? 'starting'
  const elapsed = jobStatus?.elapsed_seconds ?? 0
  const current = jobStatus?.current_watchlist
  const completed = jobStatus?.completed_watchlists ?? 0
  const total = jobStatus?.total_watchlists ?? 0
  const startedAt = jobStatus?.started_at
  const triggerType = jobStatus?.trigger_type

  // Derive live stats from events since this run started
  const sinceStart = startedAt
    ? events.filter((e) => e.timestamp >= startedAt)
    : []
  const notificationCount = sinceStart.filter((e) => e.event_type === 'notification_sent').length
  const blockedNames = sinceStart
    .filter((e) => e.event_type === 'watchlist_blocked')
    .map((e) => (e.payload.watchlist as string) ?? '')
    .filter(Boolean)

  const pct = total > 0 ? Math.round((completed / total) * 100) : 0
  const triggerLabel = triggerType && triggerType !== 'manual' ? triggerType : null
  const statusLabel = status === 'starting' ? 'Starting…' : 'Running'

  async function handleCancel() {
    setCancelling(true)
    try {
      await apiClient.cancelRun()
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobStatus() })
      void queryClient.invalidateQueries({ queryKey: queryKeys.info() })
    } finally {
      setCancelling(false)
    }
  }

  return (
    <div className="space-y-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 dark:border-blue-900/50 dark:bg-blue-950/30">
      {/* Header row */}
      <div className="flex items-center gap-3">
        <Loader2 className="h-4 w-4 flex-shrink-0 animate-spin text-blue-600 dark:text-blue-400" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-blue-900 dark:text-blue-300">
            {statusLabel}
            {triggerLabel && (
              <span className="ml-1.5 text-xs font-normal capitalize text-blue-600 dark:text-blue-400">
                · {triggerLabel}
              </span>
            )}
            {elapsed > 0 && (
              <span className="ml-2 font-normal text-blue-700 dark:text-blue-400">
                {formatElapsed(elapsed)}
              </span>
            )}
          </p>
          <p className="truncate text-xs text-blue-700 dark:text-blue-400">
            {current
              ? `${current}${total > 0 ? ` (${completed + 1} of ${total})` : ''}`
              : total > 0
                ? `0 of ${total} watchlists`
                : 'Checking seat availability…'}
          </p>
        </div>
        <button
          onClick={() => void handleCancel()}
          disabled={cancelling}
          className="ml-auto flex-shrink-0 rounded p-1 text-blue-600 hover:bg-blue-100 disabled:opacity-50 dark:text-blue-400 dark:hover:bg-blue-900/50"
          title="Cancel run"
          aria-label="Cancel run"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Progress bar */}
      {total > 0 && (
        <div className="space-y-1">
          <div className="h-1.5 w-full rounded-full bg-blue-200 dark:bg-blue-900/60">
            <div
              className="h-1.5 rounded-full bg-blue-500 transition-all duration-500 dark:bg-blue-400"
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="text-right text-[10px] tabular-nums text-blue-600 dark:text-blue-400">
            {completed}/{total} &middot; {pct}%
          </p>
        </div>
      )}

      {/* Live counters */}
      {(notificationCount > 0 || blockedNames.length > 0) && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {notificationCount > 0 && (
            <span className={cn('flex items-center gap-1 font-medium', 'text-emerald-700 dark:text-emerald-400')}>
              <Bell className="h-3 w-3" />
              {notificationCount} notification{notificationCount !== 1 ? 's' : ''}
            </span>
          )}
          {blockedNames.length > 0 && (
            <span className="flex items-center gap-1 font-medium text-amber-700 dark:text-amber-400">
              <ShieldAlert className="h-3 w-3" />
              Blocked: {blockedNames.join(', ')}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
