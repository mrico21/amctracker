import { AlertTriangle } from 'lucide-react'
import type { FailureBreakdown } from '@/api/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface FailureBreakdownCardProps {
  breakdown: FailureBreakdown
}

const FAILURE_LABELS: Array<{ key: keyof FailureBreakdown; label: string; description: string }> = [
  { key: 'challenge_pages', label: 'Challenge pages', description: 'CAPTCHA or bot-check pages returned' },
  { key: 'expired_urls', label: 'Expired URLs', description: 'Showtime URL is no longer valid' },
  { key: 'parse_errors', label: 'Parse errors', description: 'Seat data could not be extracted' },
  { key: 'playwright_errors', label: 'Playwright errors', description: 'Browser automation failure' },
]

export function FailureBreakdownCard({ breakdown }: FailureBreakdownCardProps) {
  const total = Object.values(breakdown).reduce((sum, v) => sum + v, 0)
  if (total === 0) return null

  return (
    <Card className="border-destructive/30 bg-destructive/5 dark:bg-destructive/10">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-destructive" />
          <CardTitle className="text-base text-destructive">Failure Breakdown</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {FAILURE_LABELS.map(({ key, label, description }) => {
            const count = breakdown[key]
            if (count === 0) return null
            return (
              <div key={key} className="flex items-start gap-2.5">
                <div className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-destructive/15">
                  <span className="text-xs font-bold text-destructive">{count}</span>
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">{label}</p>
                  <p className="text-xs text-muted-foreground">{description}</p>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
