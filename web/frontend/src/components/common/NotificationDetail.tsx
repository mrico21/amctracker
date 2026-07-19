import { Bell } from 'lucide-react'
import type { NotificationSummary } from '@/types/view-models'
import { cn } from '@/lib/utils'

// ── Render helpers ────────────────────────────────────────────────────────────

function renderSummaryLine(summary: NotificationSummary): string {
  const { notificationType, seats, change, windowSize } = summary

  // Priority 1: structured payload
  if (notificationType === 'watch_seats' && seats.length > 0) {
    const seatStr = seats.join(', ')
    const changeStr = change ? `: ${change.replace('->', '→')}` : ''
    return `${seatStr}${changeStr}`
  }

  if (notificationType === 'watch_any' && seats.length > 0) {
    return `Newly available: ${seats.join(', ')}`
  }

  if (notificationType === 'watch_adjacent' && seats.length > 0) {
    const label = windowSize ? `Adjacent (${windowSize}) available` : 'Adjacent seats available'
    return `${label}: ${seats.join(', ')}`
  }

  // Priority 2: message string (human-readable from event)
  if (summary.message && summary.message.trim().length > 0) {
    return summary.message
  }

  // Priority 3: generic fallback
  return 'Notification sent'
}

function labelForType(type: NotificationSummary['notificationType']): string {
  switch (type) {
    case 'watch_seats': return 'Specific seat'
    case 'watch_any': return 'Any seat'
    case 'watch_adjacent': return 'Adjacent seats'
    default: return 'Notification'
  }
}

// ── Main component ────────────────────────────────────────────────────────────

interface NotificationDetailProps {
  summaries: NotificationSummary[]
  className?: string
}

export function NotificationDetail({ summaries, className }: NotificationDetailProps) {
  if (summaries.length === 0) return null

  return (
    <div className={cn('space-y-1.5', className)}>
      {summaries.map((summary, i) => (
        <div
          key={i}
          className="flex items-start gap-2 rounded-md bg-emerald-50 px-3 py-2 dark:bg-emerald-950/30"
        >
          <Bell className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-emerald-600 dark:text-emerald-400" />
          <div className="min-w-0">
            <p className="text-xs font-semibold text-emerald-800 dark:text-emerald-300">
              {labelForType(summary.notificationType)}
            </p>
            <p className="text-xs text-emerald-700 dark:text-emerald-400">
              {renderSummaryLine(summary)}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}
