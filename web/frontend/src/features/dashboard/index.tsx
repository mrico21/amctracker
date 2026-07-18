import { AlertCircle, Play } from 'lucide-react'
import { useState } from 'react'
import { AppHeader } from '@/components/common/AppHeader'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { ErrorState } from '@/components/common/ErrorState'
import { PageContainer } from '@/components/common/PageContainer'
import { Button } from '@/components/ui/button'
import { useHealth } from '@/hooks/useHealth'
import { useInfo } from '@/hooks/useInfo'
import { useJobStatus } from '@/hooks/useJobStatus'
import { useLatestRun } from '@/hooks/useLatestRun'
import { useTriggerRun } from '@/hooks/useTriggerRun'
import { DashboardStats } from './components/DashboardStats'
import { HealthCard } from './components/HealthCard'
import { LatestRunCard } from './components/LatestRunCard'
import { RunProgressBanner } from './components/RunProgressBanner'
import { useRunCompletion } from './hooks/useRunCompletion'

export default function Dashboard() {
  const [confirmOpen, setConfirmOpen] = useState(false)

  const infoQuery = useInfo()
  const healthQuery = useHealth()
  const latestRunQuery = useLatestRun()
  const triggerRun = useTriggerRun()

  const info = infoQuery.data
  const infoRunning = info?.run_in_progress ?? false

  // Poll job status whenever a run is active (info says running, or trigger was just fired)
  const jobStatusActive = infoRunning || triggerRun.isPending || triggerRun.isSuccess
  const jobStatusQuery = useJobStatus(jobStatusActive)
  const jobStatus = jobStatusQuery.data

  // Treat as running if info reports it OR the job status says so (covers the 202→first-poll gap)
  const activeJobStatus = jobStatus?.status
  const isRunning =
    infoRunning ||
    activeJobStatus === 'starting' ||
    activeJobStatus === 'running'

  // Invalidate caches when a run transitions from in-progress → done
  useRunCompletion(infoRunning)

  if (infoQuery.isError) {
    return (
      <PageContainer>
        <ErrorState
          title="Cannot reach backend"
          error={infoQuery.error}
          onRetry={() => void infoQuery.refetch()}
        />
      </PageContainer>
    )
  }

  return (
    <PageContainer>
      <AppHeader
        title="Dashboard"
        description={info?.hostname ? `Running on ${info.hostname}` : undefined}
        actions={
          <Button
            size="sm"
            onClick={() => setConfirmOpen(true)}
            disabled={isRunning || triggerRun.isPending}
          >
            <Play className="h-4 w-4" />
            {isRunning ? 'Running…' : 'Run Now'}
          </Button>
        }
      />

      {isRunning && <RunProgressBanner jobStatus={jobStatus} />}

      {triggerRun.isError && (
        <div className="flex items-start gap-2.5 rounded-xl border border-destructive/20 bg-destructive/10 px-4 py-3">
          <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-destructive" />
          <p className="text-sm text-destructive">{triggerRun.error.message}</p>
        </div>
      )}

      <DashboardStats info={info} latestRun={latestRunQuery.data} />

      <div className="grid gap-4 md:grid-cols-2">
        <LatestRunCard
          run={latestRunQuery.data}
          isLoading={latestRunQuery.isLoading}
        />
        <HealthCard
          health={healthQuery.data}
          hostname={info?.hostname}
          trackerVersion={info?.tracker_version}
        />
      </div>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Start a tracker run?"
        description="AMCTracker will check seat availability for all enabled watchlists. This takes 1–4 minutes."
        confirmLabel="Run Now"
        onConfirm={() => triggerRun.mutate()}
      />
    </PageContainer>
  )
}
