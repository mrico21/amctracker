import { Lock, Monitor, Moon, Sun } from 'lucide-react'
import { useState } from 'react'
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
import { useUpdateSettings } from '@/hooks/useUpdateSettings'
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

function ToggleRow({
  label,
  description,
  checked,
  onChange,
  disabled,
}: {
  label: string
  description?: string
  checked: boolean
  onChange: (v: boolean) => void
  disabled?: boolean
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-3 first:pt-0 last:pb-0">
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
      </div>
      <button
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative inline-flex h-5 w-9 flex-shrink-0 rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          checked ? 'bg-primary' : 'bg-input',
          disabled && 'opacity-50 cursor-not-allowed',
        )}
      >
        <span
          className={cn(
            'pointer-events-none block h-4 w-4 rounded-full bg-background shadow-lg ring-0 transition-transform',
            checked ? 'translate-x-4' : 'translate-x-0',
          )}
        />
      </button>
    </div>
  )
}

function NumberInput({
  label,
  value,
  onChange,
  min,
  max,
  suffix,
  disabled,
}: {
  label: string
  value: number
  onChange: (v: number) => void
  min?: number
  max?: number
  suffix?: string
  disabled?: boolean
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
      <p className="flex-shrink-0 text-sm text-muted-foreground">{label}</p>
      <div className="flex items-center gap-1.5">
        <input
          type="number"
          value={value}
          min={min}
          max={max}
          disabled={disabled}
          onChange={(e) => {
            const n = parseInt(e.target.value, 10)
            if (!isNaN(n)) onChange(n)
          }}
          className={cn(
            'w-20 rounded-md border border-input bg-background px-2.5 py-1 text-right text-sm font-mono text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-ring',
            disabled && 'opacity-50 cursor-not-allowed',
          )}
        />
        {suffix && <span className="text-xs text-muted-foreground">{suffix}</span>}
      </div>
    </div>
  )
}

function TimeInput({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  disabled?: boolean
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
      <p className="flex-shrink-0 text-sm text-muted-foreground">{label}</p>
      <input
        type="time"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          'rounded-md border border-input bg-background px-2.5 py-1 text-sm font-mono text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-ring',
          disabled && 'opacity-50 cursor-not-allowed',
        )}
      />
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function Settings() {
  const settingsQuery = useSettings()
  const infoQuery = useInfo()
  const { theme, setTheme } = useTheme()
  const updateSettings = useUpdateSettings()

  // Local draft for scheduler settings — avoids spamming PUT on every keystroke
  const [schedulerDraft, setSchedulerDraft] = useState<null | {
    scheduler_enabled: boolean
    scheduler_min_interval_seconds: number
    scheduler_max_interval_seconds: number
    scheduler_quiet_hours_enabled: boolean
    scheduler_quiet_hours_start: string
    scheduler_quiet_hours_end: string
    scheduler_randomize_order: boolean
  }>(null)

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

  // Merge persisted settings with any local edits
  const sched = schedulerDraft ?? {
    scheduler_enabled: settings.scheduler_enabled,
    scheduler_min_interval_seconds: settings.scheduler_min_interval_seconds,
    scheduler_max_interval_seconds: settings.scheduler_max_interval_seconds,
    scheduler_quiet_hours_enabled: settings.scheduler_quiet_hours_enabled,
    scheduler_quiet_hours_start: settings.scheduler_quiet_hours_start,
    scheduler_quiet_hours_end: settings.scheduler_quiet_hours_end,
    scheduler_randomize_order: settings.scheduler_randomize_order,
  }

  function patchSched(patch: Partial<typeof sched>) {
    setSchedulerDraft({ ...sched, ...patch })
  }

  function saveScheduler() {
    updateSettings.mutate(
      { ...settings, ...sched },
      {
        onSuccess: () => setSchedulerDraft(null),
      },
    )
  }

  const schedDirty =
    schedulerDraft !== null &&
    JSON.stringify(schedulerDraft) !==
      JSON.stringify({
        scheduler_enabled: settings.scheduler_enabled,
        scheduler_min_interval_seconds: settings.scheduler_min_interval_seconds,
        scheduler_max_interval_seconds: settings.scheduler_max_interval_seconds,
        scheduler_quiet_hours_enabled: settings.scheduler_quiet_hours_enabled,
        scheduler_quiet_hours_start: settings.scheduler_quiet_hours_start,
        scheduler_quiet_hours_end: settings.scheduler_quiet_hours_end,
        scheduler_randomize_order: settings.scheduler_randomize_order,
      })

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

      {/* ── Scheduling ── */}
      <div className="space-y-3">
        <SectionHeader title="Scheduling" />
        <Card>
          <CardContent className="p-4 divide-y">
            <ToggleRow
              label="Enable scheduler"
              description="Automatically trigger runs at randomised intervals"
              checked={sched.scheduler_enabled}
              onChange={(v) => patchSched({ scheduler_enabled: v })}
            />
            <NumberInput
              label="Min interval"
              value={sched.scheduler_min_interval_seconds}
              onChange={(v) => patchSched({ scheduler_min_interval_seconds: v })}
              min={60}
              suffix="s"
              disabled={!sched.scheduler_enabled}
            />
            <NumberInput
              label="Max interval"
              value={sched.scheduler_max_interval_seconds}
              onChange={(v) => patchSched({ scheduler_max_interval_seconds: v })}
              min={sched.scheduler_min_interval_seconds}
              suffix="s"
              disabled={!sched.scheduler_enabled}
            />
            <ToggleRow
              label="Randomize watchlist order"
              description="Shuffle enabled watchlists before each automatic run"
              checked={sched.scheduler_randomize_order}
              onChange={(v) => patchSched({ scheduler_randomize_order: v })}
              disabled={!sched.scheduler_enabled}
            />
            <ToggleRow
              label="Quiet hours"
              description="Suppress automatic runs between the configured times (local time)"
              checked={sched.scheduler_quiet_hours_enabled}
              onChange={(v) => patchSched({ scheduler_quiet_hours_enabled: v })}
              disabled={!sched.scheduler_enabled}
            />
            <TimeInput
              label="Quiet hours start"
              value={sched.scheduler_quiet_hours_start}
              onChange={(v) => patchSched({ scheduler_quiet_hours_start: v })}
              disabled={!sched.scheduler_enabled || !sched.scheduler_quiet_hours_enabled}
            />
            <TimeInput
              label="Quiet hours end"
              value={sched.scheduler_quiet_hours_end}
              onChange={(v) => patchSched({ scheduler_quiet_hours_end: v })}
              disabled={!sched.scheduler_enabled || !sched.scheduler_quiet_hours_enabled}
            />
          </CardContent>
        </Card>
        {schedDirty && (
          <div className="flex items-center justify-end gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setSchedulerDraft(null)}
              disabled={updateSettings.isPending}
            >
              Discard
            </Button>
            <Button
              size="sm"
              onClick={saveScheduler}
              disabled={updateSettings.isPending}
            >
              {updateSettings.isPending ? 'Saving…' : 'Save'}
            </Button>
          </div>
        )}
        {updateSettings.isError && (
          <p className="text-sm text-destructive">{updateSettings.error.message}</p>
        )}
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
    </PageContainer>
  )
}
