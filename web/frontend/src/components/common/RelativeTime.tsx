import { cn } from '@/lib/utils'
import { formatDateTime, formatRelativeTime } from '@/lib/format'

interface RelativeTimeProps {
  iso: string | null | undefined
  className?: string
}

export function RelativeTime({ iso, className }: RelativeTimeProps) {
  if (!iso) {
    return <span className={cn(className)}>—</span>
  }
  return (
    <time dateTime={iso} title={formatDateTime(iso)} className={cn(className)}>
      {formatRelativeTime(iso)}
    </time>
  )
}
