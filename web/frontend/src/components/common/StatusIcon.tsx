import { AlertTriangle, CheckCircle, Clock, MinusCircle, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

type StatusIconSize = 'sm' | 'md'

const ICON_MAP: Record<string, { Icon: React.ElementType; iconClass: string }> = {
  success: { Icon: CheckCircle, iconClass: 'text-emerald-500' },
  running: { Icon: Clock, iconClass: 'text-blue-500' },
  partial_failure: { Icon: AlertTriangle, iconClass: 'text-amber-500' },
  skipped: { Icon: MinusCircle, iconClass: 'text-muted-foreground' },
  failed: { Icon: XCircle, iconClass: 'text-destructive' },
}

const SIZE_MAP: Record<StatusIconSize, string> = {
  sm: 'h-3.5 w-3.5',
  md: 'h-4 w-4',
}

interface StatusIconProps {
  status: string
  size?: StatusIconSize
  className?: string
}

export function StatusIcon({ status, size = 'md', className }: StatusIconProps) {
  const config = ICON_MAP[status] ?? { Icon: XCircle, iconClass: 'text-muted-foreground' }
  const { Icon, iconClass } = config
  return <Icon className={cn(SIZE_MAP[size], iconClass, className)} />
}
