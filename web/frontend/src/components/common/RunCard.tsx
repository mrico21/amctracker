import { ChevronRight, Clock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { RunHistorySummary } from '@/api/types'
import { Card, CardContent } from '@/components/ui/card'
import { formatDuration, truncateUuid } from '@/lib/format'
import { CopyButton } from './CopyButton'
import { RelativeTime } from './RelativeTime'
import { StatusBadge } from './StatusBadge'

interface RunCardProps {
  run: RunHistorySummary
}

export function RunCard({ run }: RunCardProps) {
  const navigate = useNavigate()

  return (
    <Card
      className="group cursor-pointer transition-all duration-150 hover:bg-accent/50 hover:shadow-md"
      onClick={() => void navigate(`/history/${run.run_id}`)}
    >
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <StatusBadge status={run.run_status} />
              <span
                className="font-mono text-xs text-muted-foreground"
                title={run.run_id}
              >
                {truncateUuid(run.run_id)}
              </span>
              <div onClick={(e) => e.stopPropagation()}>
                <CopyButton text={run.run_id} />
              </div>
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <RelativeTime iso={run.completed_at} />
              </span>
              <span>{formatDuration(run.duration_seconds)}</span>
            </div>
          </div>
          <div className="flex flex-shrink-0 items-center gap-3">
            <div className="text-right text-xs text-muted-foreground">
              <div>
                {run.succeeded}/{run.total_watchlists} ok
              </div>
              {run.notifications_sent > 0 && (
                <div className="font-medium text-foreground">
                  {run.notifications_sent} notif.
                </div>
              )}
            </div>
            <ChevronRight className="h-4 w-4 flex-shrink-0 text-muted-foreground/40 transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-muted-foreground" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
