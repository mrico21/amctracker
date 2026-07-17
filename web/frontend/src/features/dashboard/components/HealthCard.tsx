import type { HealthResponse } from '@/api/types'
import { HealthIndicator } from '@/components/common/HealthIndicator'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface HealthCardProps {
  health: HealthResponse | undefined
  hostname: string | undefined
  trackerVersion: string | null | undefined
}

export function HealthCard({ health, hostname, trackerVersion }: HealthCardProps) {
  const overallStatus = health?.status ?? 'unknown'

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">System</CardTitle>
          <HealthIndicator
            status={overallStatus === 'healthy' ? 'healthy' : overallStatus === 'unhealthy' ? 'unhealthy' : 'unknown'}
            label={overallStatus}
          />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Health checks */}
        {health?.checks && (
          <ul className="space-y-1.5">
            {Object.entries(health.checks).map(([name, result]) => (
              <li key={name} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{name.replace(/_/g, ' ')}</span>
                <HealthIndicator
                  status={result.status === 'ok' ? 'healthy' : 'unhealthy'}
                  label={result.status === 'ok' ? 'ok' : (result.detail ?? 'error')}
                />
              </li>
            ))}
          </ul>
        )}

        {/* System info */}
        {(hostname || trackerVersion) && (
          <div className="border-t pt-3 space-y-1">
            {hostname && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Host</span>
                <span className="font-mono text-foreground">{hostname}</span>
              </div>
            )}
            {trackerVersion && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Tracker</span>
                <span className="font-mono text-foreground">v{trackerVersion}</span>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
