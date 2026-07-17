import { Lock, Monitor, Moon, Sun } from 'lucide-react'
import { AppHeader } from '@/components/common/AppHeader'
import { ErrorState } from '@/components/common/ErrorState'
import { LoadingState } from '@/components/common/LoadingState'
import { PageContainer } from '@/components/common/PageContainer'
import { SectionHeader } from '@/components/common/SectionHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useInfo } from '@/hooks/useInfo'
import { useSettings } from '@/hooks/useSettings'
import { cn } from '@/lib/utils'
import { useTheme } from '@/providers/ThemeProvider'

// ── Local helpers ──────────────────────────────────────────────────────────────

function SettingRow({
  label,
  value,
  mono = false,
}: {
  label: string
  value: React.ReactNode
  mono?: boolean
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-3 first:pt-0 last:pb-0">
      <p className="flex-shrink-0 text-sm text-muted-foreground">{label}</p>
      <p className={cn('text-right text-sm font-medium text-foreground', mono && 'break-all font-mono')}>
        {value}
      </p>
    </div>
  )
}

function PlaceholderSection({ title, description }: { title: string; description: string }) {
  return (
    <div className="space-y-3 opacity-60">
      <SectionHeader title={title} />
      <Card>
        <CardContent className="p-4">
          <div className="flex items-start gap-2.5">
            <Lock className="mt-0.5 h-4 w-4 flex-shrink-0 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function Settings() {
  const settingsQuery = useSettings()
  const infoQuery = useInfo()
  const { theme, setTheme } = useTheme()

  if (settingsQuery.isError) {
    return (
      <PageContainer>
        <AppHeader title="Settings" />
        <ErrorState
          title="Could not load settings"
          error={settingsQuery.error}
          onRetry={() => void settingsQuery.refetch()}
        />
      </PageContainer>
    )
  }

  if (settingsQuery.isLoading) {
    return (
      <PageContainer>
        <AppHeader title="Settings" />
        <LoadingState message="Loading settings…" />
      </PageContainer>
    )
  }

  const settings = settingsQuery.data!
  const info = infoQuery.data

  return (
    <PageContainer>
      <AppHeader title="Settings" description="Backend configuration and app preferences" />

      {/* ── Appearance ── */}
      <div className="space-y-3">
        <SectionHeader title="Appearance" />
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-medium text-foreground">Theme</p>
                <p className="text-xs text-muted-foreground">Choose your preferred color scheme</p>
              </div>
              <div className="flex gap-1">
                <Button
                  size="sm"
                  variant={theme === 'light' ? 'default' : 'outline'}
                  onClick={() => setTheme('light')}
                >
                  <Sun className="h-3.5 w-3.5" />
                  Light
                </Button>
                <Button
                  size="sm"
                  variant={theme === 'dark' ? 'default' : 'outline'}
                  onClick={() => setTheme('dark')}
                >
                  <Moon className="h-3.5 w-3.5" />
                  Dark
                </Button>
                <Button
                  size="sm"
                  variant={theme === 'system' ? 'default' : 'outline'}
                  onClick={() => setTheme('system')}
                >
                  <Monitor className="h-3.5 w-3.5" />
                  System
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Tracker ── */}
      <div className="space-y-3">
        <SectionHeader title="Tracker" />
        <Card>
          <CardContent className="p-4 divide-y">
            <SettingRow label="Python executable" value={settings.python_executable} mono />
            <SettingRow label="Tracker script" value={settings.tracker_script} mono />
            <SettingRow label="Watchlist file" value={settings.watchlist_file} mono />
            <SettingRow label="Run timeout" value={`${settings.run_timeout_seconds}s`} />
          </CardContent>
        </Card>
      </div>

      {/* ── History ── */}
      <div className="space-y-3">
        <SectionHeader title="History" />
        <Card>
          <CardContent className="p-4">
            <SettingRow label="Max runs kept" value={settings.max_history_runs} />
          </CardContent>
        </Card>
      </div>

      {/* ── Network ── */}
      <div className="space-y-3">
        <SectionHeader title="Network" />
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <p className="flex-shrink-0 text-sm text-muted-foreground">CORS origins</p>
              <div className="flex flex-wrap gap-1.5 sm:justify-end">
                {settings.cors_origins.map((origin) => (
                  <Badge key={origin} variant="secondary" className="font-mono text-xs">
                    {origin}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Application ── */}
      <div className="space-y-3">
        <SectionHeader title="Application" />
        <Card>
          <CardContent className="p-4 divide-y">
            <SettingRow label="API version" value={info?.api_version ?? '—'} />
            <SettingRow label="Schema version" value={info?.schema_version ?? '—'} />
            <SettingRow label="Tracker version" value={info?.tracker_version ?? '—'} />
            <SettingRow label="Hostname" value={info?.hostname ?? '—'} mono />
          </CardContent>
        </Card>
      </div>

      {/* ── Future: Notifications ── */}
      <PlaceholderSection
        title="Notifications"
        description="Pushover notification credentials are configured in the tracker environment. In-app management is planned for a future release."
      />

      {/* ── Future: Scheduling ── */}
      <PlaceholderSection
        title="Scheduling"
        description="Automatic scheduled runs via APScheduler are planned for a future release. Currently, runs must be triggered manually or via an external cron job."
      />
    </PageContainer>
  )
}
