import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface SkeletonCardProps {
  lines?: number
  className?: string
  showHeader?: boolean
}

export function SkeletonCard({ lines = 3, className, showHeader = true }: SkeletonCardProps) {
  return (
    <Card className={className}>
      {showHeader && (
        <CardHeader className="pb-3">
          <Skeleton className="h-4 w-32" />
        </CardHeader>
      )}
      <CardContent className={cn('space-y-2', !showHeader && 'pt-6')}>
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton
            key={i}
            className={cn('h-3', i === 0 ? 'w-3/4' : i === lines - 1 ? 'w-1/2' : 'w-full')}
          />
        ))}
      </CardContent>
    </Card>
  )
}
