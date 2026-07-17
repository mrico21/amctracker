import { cn } from '@/lib/utils'

interface PageContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export function PageContainer({ children, className, ...props }: PageContainerProps) {
  return (
    <div className={cn('mx-auto w-full max-w-4xl space-y-6 px-4 py-6', className)} {...props}>
      {children}
    </div>
  )
}
