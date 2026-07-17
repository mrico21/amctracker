import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const STATUS_MAP: Record<string, { label: string; className: string }> = {
  success: { label: 'Success', className: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400' },
  partial_failure: { label: 'Partial', className: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400' },
  failed: { label: 'Failed', className: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' },
  running: { label: 'Running', className: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' },
  skipped: { label: 'Skipped', className: 'bg-secondary text-secondary-foreground' },
}

interface StatusBadgeProps {
  status: string
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_MAP[status] ?? { label: status, className: 'bg-secondary text-secondary-foreground' }
  return (
    <Badge className={cn(config.className, className)}>
      {config.label}
    </Badge>
  )
}
