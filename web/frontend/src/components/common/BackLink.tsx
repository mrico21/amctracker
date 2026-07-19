import { ChevronLeft } from 'lucide-react'
import { Link } from 'react-router-dom'

interface BackLinkProps {
  to: string
  children: React.ReactNode
}

export function BackLink({ to, children }: BackLinkProps) {
  return (
    <Link
      to={to}
      className="flex w-fit items-center gap-1 rounded-sm text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <ChevronLeft className="h-4 w-4" />
      {children}
    </Link>
  )
}
