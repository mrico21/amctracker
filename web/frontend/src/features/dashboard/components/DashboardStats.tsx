import { Bell, CheckCircle, Clock, List } from 'lucide-react'
import type { InfoResponse, RunResult } from '@/api/types'
import { StatCard } from '@/components/common/StatCard'
import { formatRelativeTime } from '@/lib/format'
import { cn } from '@/lib/utils'

interface DashboardStatsProps {
  info: InfoResponse | undefined
  latestRun: RunResult | null | undefined
}

const STATUS_STYLES: Record<string, { label: string; className: string }> = {
  success: { label: 'Success', className: 'text-emerald-600 dark:text-emerald-400' },
  partial_failure: { label: 'Partial', className: 'text-amber-600 dark:text-amber-400' },
  failed: { label: 'Failed', className: 'text-red-500 dark:text-red-400' },
}

function StatusValue({ status }: { status: string | null | undefined }) {
  if (!status) return <span>—</span>
  const style = STATUS_STYLES[status] ?? { label: status, className: 'text-foreground' }
  return <span className={cn(style.className)}>{style.label}</span>
}

export function DashboardStats({ info, latestRun }: DashboardStatsProps) {
  const summary = latestRun?.summary

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <StatCard
        label="Last Run"
        value={formatRelativeTime(info?.last_run_at)}
        icon={<Clock className="h-4 w-4" />}
      />
      <StatCard
        label="Status"
        value={<StatusValue status={info?.last_run_status} />}
        icon={<CheckCircle className="h-4 w-4" />}
      />
      <StatCard
        label="Watchlists"
        value={summary ? `${summary.succeeded}/${summary.total_watchlists}` : '—'}
        description={summary?.failed ? `${summary.failed} failed` : undefined}
        valueClassName={summary?.failed ? 'text-destructive' : undefined}
        icon={<List className="h-4 w-4" />}
      />
      <StatCard
        label="Notifications"
        value={summary?.notifications_sent ?? '—'}
        valueClassName={summary?.notifications_sent ? 'text-emerald-600 dark:text-emerald-400' : undefined}
        icon={<Bell className="h-4 w-4" />}
      />
    </div>
  )
}
