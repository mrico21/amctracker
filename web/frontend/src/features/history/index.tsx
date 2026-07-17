import { Clock } from 'lucide-react'
import { AppHeader } from '@/components/common/AppHeader'
import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { PageContainer } from '@/components/common/PageContainer'
import { RunCard } from '@/components/common/RunCard'
import { useHistory } from '@/hooks/useHistory'
import { SkippedFilesWarning } from './components/SkippedFilesWarning'

export default function History() {
  const historyQuery = useHistory()

  if (historyQuery.isError) {
    return (
      <PageContainer>
        <AppHeader title="History" />
        <ErrorState
          title="Could not load history"
          error={historyQuery.error}
          onRetry={() => void historyQuery.refetch()}
        />
      </PageContainer>
    )
  }

  if (historyQuery.isLoading) {
    return (
      <PageContainer>
        <AppHeader title="History" />
        <LoadingState message="Loading run history…" />
      </PageContainer>
    )
  }

  const runs = historyQuery.data?.runs ?? []
  const skippedFiles = historyQuery.data?.skipped_files ?? []

  const description =
    runs.length === 1
      ? '1 run recorded'
      : runs.length > 1
        ? `${runs.length} runs recorded`
        : undefined

  return (
    <PageContainer>
      <AppHeader title="History" description={description} />

      {skippedFiles.length > 0 && (
        <SkippedFilesWarning skippedFiles={skippedFiles} />
      )}

      {runs.length === 0 ? (
        <EmptyState
          icon={<Clock className="h-10 w-10" />}
          title="No runs recorded yet"
          description="Run the tracker from the Dashboard to see history appear here."
        />
      ) : (
        <div className="space-y-2">
          {runs.map((run) => (
            <RunCard key={run.run_id} run={run} />
          ))}
        </div>
      )}
    </PageContainer>
  )
}
