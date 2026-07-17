import { cn } from '@/lib/utils'

interface HealthIndicatorProps {
  status: 'healthy' | 'unhealthy' | 'unknown'
  label?: string
  className?: string
}

export function HealthIndicator({ status, label, className }: HealthIndicatorProps) {
  return (
    <div className={cn('flex items-center gap-1.5', className)}>
      <span
        className={cn('h-2 w-2 rounded-full flex-shrink-0', {
          'bg-emerald-500': status === 'healthy',
          'bg-red-500': status === 'unhealthy',
          'bg-muted-foreground': status === 'unknown',
        })}
      />
      {label && <span className="text-sm text-muted-foreground">{label}</span>}
    </div>
  )
}
