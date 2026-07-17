import { ChevronLeft } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { AppHeader } from '@/components/common/AppHeader'
import { CopyButton } from '@/components/common/CopyButton'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { PageContainer } from '@/components/common/PageContainer'
import { RelativeTime } from '@/components/common/RelativeTime'
import { SectionHeader } from '@/components/common/SectionHeader'
import { StatusBadge } from '@/components/common/StatusBadge'
import { formatDuration, truncateUuid } from '@/lib/format'
import { useHistoryRun } from '@/hooks/useHistory'
import { FailureBreakdownCard } from './components/FailureBreakdownCard'
import { RunSummaryStats } from './components/RunSummaryStats'
import { WatchlistResultCard } from './components/WatchlistResultCard'

export default function RunDetails() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const runQuery = useHistoryRun(runId ?? '')

  const goBack = () => void navigate('/history')

  if (runQuery.isError) {
    return (
      <PageContainer>
        <button
          onClick={goBack}
          className="flex items-center gap-1 rounded-sm text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronLeft className="h-4 w-4" />
          History
        </button>
        <AppHeader title="Run Details" />
        <ErrorState
          title="Could not load run"
          error={runQuery.error}
          onRetry={() => void runQuery.refetch()}
        />
      </PageContainer>
    )
  }

  if (runQuery.isLoading) {
    return (
      <PageContainer>
        <button
          onClick={goBack}
          className="flex items-center gap-1 rounded-sm text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronLeft className="h-4 w-4" />
          History
        </button>
        <AppHeader title="Run Details" />
        <LoadingState message="Loading run details…" />
      </PageContainer>
    )
  }

  const run = runQuery.data!

  const watchlistSummary = [
    `${run.summary.total_watchlists} total`,
    run.summary.succeeded > 0 && `${run.summary.succeeded} succeeded`,
    run.summary.failed > 0 && `${run.summary.failed} failed`,
    run.summary.disabled > 0 && `${run.summary.disabled} disabled`,
  ]
    .filter(Boolean)
    .join(' · ')

  return (
    <PageContainer>
      {/* Back navigation */}
      <button
        onClick={goBack}
        className="flex items-center gap-1 rounded-sm text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ChevronLeft className="h-4 w-4" />
        History
      </button>

      {/* Page header group — tightly spaced */}
      <div className="space-y-4">
        <AppHeader
          title="Run Details"
          description={`${run.tracker_version} · ${run.hostname}`}
        />

        {/* Identity strip: status + run ID + duration */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <StatusBadge status={run.run_status} />
          <div
            className="flex items-center gap-1 font-mono text-xs text-muted-foreground"
            title={run.run_id}
          >
            {truncateUuid(run.run_id)}
            <CopyButton text={run.run_id} />
          </div>
          <span className="text-xs text-muted-foreground">
            {formatDuration(run.duration_seconds)}
          </span>
        </div>

        {/* Timestamps */}
        <div className="flex flex-wrap gap-x-8 gap-y-3">
          <div className="space-y-0.5">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Started
            </p>
            <RelativeTime iso={run.started_at} className="text-sm" />
          </div>
          <div className="space-y-0.5">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Completed
            </p>
            <RelativeTime iso={run.completed_at} className="text-sm" />
          </div>
        </div>
      </div>

      {/* Status overview */}
      <RunSummaryStats summary={run.summary} />

      {/* Failure breakdown — only rendered when failures exist */}
      <FailureBreakdownCard breakdown={run.failure_breakdown} />

      {/* Watchlist results */}
      <div className="space-y-3">
        <SectionHeader
          title="Watchlists"
          description={watchlistSummary}
        />
        {run.watchlists.length === 0 ? (
          <EmptyState
            title="No watchlist results"
            description="No watchlists were configured for this run."
          />
        ) : (
          <div className="space-y-2">
            {run.watchlists.map((result) => (
              <WatchlistResultCard key={result.name} result={result} />
            ))}
          </div>
        )}
      </div>
    </PageContainer>
  )
}
