import { useNavigate } from 'react-router-dom'
import type { RunResult } from '@/api/types'
import { CopyButton } from '@/components/common/CopyButton'
import { EmptyState } from '@/components/common/EmptyState'
import { StatusBadge } from '@/components/common/StatusBadge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { formatDateTime, formatDuration, truncateUuid } from '@/lib/format'
import { WatchlistResultsList } from './WatchlistResultsList'

interface LatestRunCardProps {
  run: RunResult | null | undefined
  isLoading: boolean
}

export function LatestRunCard({ run, isLoading }: LatestRunCardProps) {
  const navigate = useNavigate()

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">Latest Run</CardTitle>
          {run && <StatusBadge status={run.run_status} />}
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {isLoading ? (
          <div className="space-y-2 py-4">
            <Skeleton className="h-3 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ) : !run ? (
          <EmptyState
            title="No runs yet"
            description="Trigger your first run to see results here."
            className="py-8"
          />
        ) : (
          <div className="space-y-4">
            {/* Run metadata */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span>{formatDateTime(run.completed_at)}</span>
              <span>{formatDuration(run.duration_seconds)}</span>
              <span className="flex items-center gap-1 font-mono">
                {truncateUuid(run.run_id)}
                <CopyButton text={run.run_id} />
              </span>
            </div>

            {/* Watchlist results */}
            <WatchlistResultsList results={run.watchlists} />

            {/* Link to full details */}
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-muted-foreground"
              onClick={() => void navigate(`/history/${run.run_id}`)}
            >
              View full run details
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
