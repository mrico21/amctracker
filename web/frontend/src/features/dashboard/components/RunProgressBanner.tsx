import { Loader2, X } from 'lucide-react'
import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'
import type { JobStatus } from '@/api/types'

interface RunProgressBannerProps {
  jobStatus: JobStatus | undefined
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}m ${s}s`
}

export function RunProgressBanner({ jobStatus }: RunProgressBannerProps) {
  const queryClient = useQueryClient()
  const [cancelling, setCancelling] = useState(false)

  const status = jobStatus?.status ?? 'starting'
  const elapsed = jobStatus?.elapsed_seconds ?? 0
  const current = jobStatus?.current_watchlist
  const completed = jobStatus?.completed_watchlists ?? 0
  const total = jobStatus?.total_watchlists ?? 0

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
    <div className="flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 dark:border-blue-900/50 dark:bg-blue-950/30">
      <Loader2 className="h-4 w-4 flex-shrink-0 animate-spin text-blue-600 dark:text-blue-400" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-blue-900 dark:text-blue-300">
          {statusLabel}
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
  )
}
