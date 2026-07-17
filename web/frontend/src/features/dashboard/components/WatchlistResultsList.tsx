import { Bell } from 'lucide-react'
import type { WatchlistRunResult } from '@/api/types'
import { StatusIcon } from '@/components/common/StatusIcon'
import { cn } from '@/lib/utils'

interface WatchlistResultRowProps {
  result: WatchlistRunResult
}

function WatchlistResultRow({ result }: WatchlistResultRowProps) {
  const hasSeats = result.seats_available > 0 || result.adjacent_windows_available > 0

  return (
    <li className="flex items-start justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
      <div className="flex min-w-0 flex-1 items-start gap-2.5">
        <StatusIcon status={result.status} size="md" className="mt-0.5 flex-shrink-0" />
        <div className="min-w-0">
          <p className={cn('text-sm font-medium', !result.enabled && 'text-muted-foreground')}>
            {result.name}
          </p>
          {result.error_message && (
            <p className="mt-0.5 text-xs text-destructive">{result.error_message}</p>
          )}
        </div>
      </div>
      <div className="flex flex-shrink-0 items-center gap-1.5 text-right">
        {hasSeats && (
          <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
            {result.seats_available > 0
              ? `${result.seats_available} seat${result.seats_available !== 1 ? 's' : ''}`
              : `${result.adjacent_windows_available} window${result.adjacent_windows_available !== 1 ? 's' : ''}`}
          </span>
        )}
        {result.notification_sent && (
          <Bell className="h-3.5 w-3.5 text-emerald-500" aria-label="Notification sent" />
        )}
      </div>
    </li>
  )
}

interface WatchlistResultsListProps {
  results: WatchlistRunResult[]
}

export function WatchlistResultsList({ results }: WatchlistResultsListProps) {
  const active = results.filter((r) => r.enabled)
  if (active.length === 0) return null

  return (
    <ul className="divide-y">
      {active.map((result) => (
        <WatchlistResultRow key={result.name} result={result} />
      ))}
    </ul>
  )
}
