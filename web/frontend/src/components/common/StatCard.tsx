import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: React.ReactNode
  description?: string
  icon?: React.ReactNode
  valueClassName?: string
  className?: string
}

export function StatCard({ label, value, description, icon, valueClassName, className }: StatCardProps) {
  return (
    <Card className={className}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
          {icon && <span className="text-muted-foreground">{icon}</span>}
        </div>
        <div className="mt-2">
          <span className={cn('text-2xl font-bold text-foreground leading-none', valueClassName)}>
            {value ?? '—'}
          </span>
          {description && (
            <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
