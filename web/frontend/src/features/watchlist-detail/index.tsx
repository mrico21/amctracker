import { ExternalLink, EyeOff } from 'lucide-react'
import { useParams } from 'react-router-dom'
import { AppHeader } from '@/components/common/AppHeader'
import { BackLink } from '@/components/common/BackLink'
import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { MonitoringConfig } from '@/components/common/MonitoringConfig'
import { PageContainer } from '@/components/common/PageContainer'
import { SectionHeader } from '@/components/common/SectionHeader'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { useWatchlist } from '@/hooks/useWatchlist'
import { useWatchlistEvents } from '@/hooks/useWatchlistEvents'
import { deriveCurrentAvailability, deriveWatchlistHealth } from '@/lib/activity'
import { WatchlistActivityTimeline } from './components/WatchlistActivityTimeline'
import { WatchlistStatusCard } from './components/WatchlistStatusCard'

export default function WatchlistDetail() {
  const { id = '' } = useParams<{ id: string }>()

  const watchlistQuery = useWatchlist(id)
  const { events, isLoading: eventsLoading } = useWatchlistEvents(
    watchlistQuery.data?.name ?? '',
  )

  if (watchlistQuery.isError) {
    return (
      <PageContainer>
        <BackLink to="/watchlists">Watchlists</BackLink>
        <ErrorState
          title="Could not load watchlist"
          error={watchlistQuery.error}
          onRetry={() => void watchlistQuery.refetch()}
        />
      </PageContainer>
    )
  }

  if (watchlistQuery.isLoading) {
    return (
      <PageContainer>
        <BackLink to="/watchlists">Watchlists</BackLink>
        <LoadingState message="Loading watchlist…" />
      </PageContainer>
    )
  }

  const watchlist = watchlistQuery.data!

  // ── Derived view models ─────────────────────────────────────────────────────

  const health = deriveWatchlistHealth(events)
  const availability = deriveCurrentAvailability(events)
  const eventsReady = !eventsLoading

  return (
    <PageContainer>
      <BackLink to="/watchlists">Watchlists</BackLink>

      {/* Header */}
      <AppHeader
        title={watchlist.name}
        actions={
          <div className="flex items-center gap-2">
            {!watchlist.enabled && (
              <Badge variant="outline" className="gap-1">
                <EyeOff className="h-3 w-3" />
                Disabled
              </Badge>
            )}
            <a
              href={watchlist.showtime_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
              title="Open showtime on AMC"
            >
              <ExternalLink className="h-4 w-4" />
              AMC
            </a>
          </div>
        }
      />

      {/* Current Status — first thing visible */}
      <WatchlistStatusCard
        health={health}
        availability={availability}
        isLoading={!eventsReady}
      />

      {/* Monitoring configuration */}
      <div className="space-y-3">
        <SectionHeader title="Monitoring" />
        <Card>
          <CardContent className="p-4">
            <MonitoringConfig
              watch_seats={watchlist.watch_seats}
              watch_any={watchlist.watch_any}
              watch_adjacent={watchlist.watch_adjacent}
              defaultExpanded
            />
          </CardContent>
        </Card>
      </div>

      {/* Recent activity for this watchlist */}
      <WatchlistActivityTimeline events={events} isLoading={!eventsReady} maxEvents={20} />
    </PageContainer>
  )
}
