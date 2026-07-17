import { Tv2 } from 'lucide-react'
import type { WatchlistRunResult } from '@/api/types'
import { AppHeader } from '@/components/common/AppHeader'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { PageContainer } from '@/components/common/PageContainer'
import { WatchlistCard } from '@/components/common/WatchlistCard'
import { useLatestRun } from '@/hooks/useLatestRun'
import { useWatchlists } from '@/hooks/useWatchlists'

export default function Watchlists() {
  const watchlistsQuery = useWatchlists()
  const latestRunQuery = useLatestRun()

  if (watchlistsQuery.isError) {
    return (
      <PageContainer>
        <AppHeader title="Watchlists" />
        <ErrorState
          title="Could not load watchlists"
          error={watchlistsQuery.error}
          onRetry={() => void watchlistsQuery.refetch()}
        />
      </PageContainer>
    )
  }

  if (watchlistsQuery.isLoading) {
    return (
      <PageContainer>
        <AppHeader title="Watchlists" />
        <LoadingState message="Loading watchlists…" />
      </PageContainer>
    )
  }

  const watchlists = watchlistsQuery.data ?? []
  const enabledCount = watchlists.filter((w) => w.enabled).length
  const totalCount = watchlists.length

  const description =
    totalCount === 0
      ? undefined
      : enabledCount === totalCount
        ? `${totalCount} watchlist${totalCount !== 1 ? 's' : ''}`
        : `${enabledCount} enabled · ${totalCount} total`

  // Build name → result lookup from the latest run (supplementary, non-blocking)
  const resultByName: Record<string, WatchlistRunResult> = {}
  if (latestRunQuery.data?.watchlists) {
    for (const result of latestRunQuery.data.watchlists) {
      resultByName[result.name] = result
    }
  }

  return (
    <PageContainer>
      <AppHeader title="Watchlists" description={description} />

      {watchlists.length === 0 ? (
        <EmptyState
          icon={<Tv2 className="h-10 w-10" />}
          title="No watchlists configured"
          description="Add a showtime to track using the tracker CLI with --add."
        />
      ) : (
        <div className="space-y-2">
          {watchlists.map((watchlist) => (
            <WatchlistCard
              key={watchlist.id}
              watchlist={watchlist}
              latestResult={resultByName[watchlist.name]}
            />
          ))}
        </div>
      )}
    </PageContainer>
  )
}
