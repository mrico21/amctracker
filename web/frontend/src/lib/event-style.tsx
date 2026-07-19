import {
  AlertTriangle,
  Bell,
  Calendar,
  CalendarClock,
  CheckCircle,
  CircleDashed,
  Play,
  SkipForward,
  XCircle,
} from 'lucide-react'
import type { ActivityEventType } from '@/api/types'

export type EventStyle = { icon: React.ReactNode; color: string; muted: boolean }

export function getEventStyle(type: ActivityEventType): EventStyle {
  switch (type) {
    case 'run_start':
      return { icon: <Play className="h-3.5 w-3.5" />, color: 'text-blue-600 dark:text-blue-400', muted: false }
    case 'run_complete':
      return { icon: <CheckCircle className="h-3.5 w-3.5" />, color: 'text-emerald-600 dark:text-emerald-400', muted: false }
    case 'run_cancelled':
      return { icon: <XCircle className="h-3.5 w-3.5" />, color: 'text-red-500 dark:text-red-400', muted: false }
    case 'watchlist_start':
      return { icon: <CircleDashed className="h-3.5 w-3.5" />, color: 'text-muted-foreground', muted: true }
    case 'watchlist_complete':
      return { icon: <CheckCircle className="h-3.5 w-3.5" />, color: 'text-emerald-600 dark:text-emerald-400', muted: true }
    case 'watchlist_blocked':
      return { icon: <AlertTriangle className="h-3.5 w-3.5" />, color: 'text-amber-600 dark:text-amber-400', muted: false }
    case 'watchlist_failed':
      return { icon: <XCircle className="h-3.5 w-3.5" />, color: 'text-red-500 dark:text-red-400', muted: false }
    case 'notification_sent':
      return { icon: <Bell className="h-3.5 w-3.5" />, color: 'text-emerald-600 dark:text-emerald-400', muted: false }
    case 'scheduler_triggered':
      return { icon: <Calendar className="h-3.5 w-3.5" />, color: 'text-blue-500 dark:text-blue-400', muted: false }
    case 'scheduler_skipped':
      return { icon: <SkipForward className="h-3.5 w-3.5" />, color: 'text-muted-foreground', muted: true }
    default:
      return { icon: <CalendarClock className="h-3.5 w-3.5" />, color: 'text-muted-foreground', muted: true }
  }
}
