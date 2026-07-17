import { Bell, CheckCircle, List, XCircle } from 'lucide-react'
import type { RunSummary } from '@/api/types'
import { StatCard } from '@/components/common/StatCard'

interface RunSummaryStatsProps {
  summary: RunSummary
}

export function RunSummaryStats({ summary }: RunSummaryStatsProps) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <StatCard
        label="Total"
        value={summary.total_watchlists}
        description={summary.disabled > 0 ? `${summary.disabled} disabled` : undefined}
        icon={<List className="h-4 w-4" />}
      />
      <StatCard
        label="Succeeded"
        value={summary.succeeded}
        valueClassName={summary.succeeded > 0 ? 'text-emerald-600 dark:text-emerald-400' : undefined}
        icon={<CheckCircle className="h-4 w-4" />}
      />
      <StatCard
        label="Failed"
        value={summary.failed}
        valueClassName={summary.failed > 0 ? 'text-destructive' : undefined}
        icon={<XCircle className="h-4 w-4" />}
      />
      <StatCard
        label="Notifications"
        value={summary.notifications_sent}
        valueClassName={
          summary.notifications_sent > 0 ? 'text-emerald-600 dark:text-emerald-400' : undefined
        }
        icon={<Bell className="h-4 w-4" />}
      />
    </div>
  )
}
