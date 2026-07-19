// ── Watchlist ─────────────────────────────────────────────────────────────────

export interface WatchlistAdjacentConfig {
  rows: string[]
  count: number
}

export interface WatchlistEntry {
  id: string
  index: number
  name: string
  enabled: boolean
  showtime_url: string
  watch_seats: string[]
  watch_any: string[]
  watch_adjacent: WatchlistAdjacentConfig[]
}

// ── Run result ────────────────────────────────────────────────────────────────

export interface WatchlistRunMonitoring {
  watch_seats: string[]
  watch_any: string[]
  watch_adjacent: WatchlistAdjacentConfig[]
}

export interface WatchlistRunResult {
  name: string
  enabled: boolean
  showtime_url: string
  monitoring: WatchlistRunMonitoring
  status: string
  seats_available: number
  adjacent_windows_available: number
  notification_sent: boolean
  failure_type: string | null
  error_message: string | null
}

export interface RunSummary {
  total_watchlists: number
  succeeded: number
  disabled: number
  failed: number
  notifications_sent: number
  cache_hits: number
  cache_misses: number
}

export interface FailureBreakdown {
  challenge_pages: number
  expired_urls: number
  parse_errors: number
  playwright_errors: number
}

export interface RunResult {
  schema_version: number
  generated_by: string
  generated_at: string
  run_id: string
  started_at: string
  completed_at: string
  duration_seconds: number
  tracker_version: string
  hostname: string
  run_status: string
  summary: RunSummary
  failure_breakdown: FailureBreakdown
  watchlists: WatchlistRunResult[]
}

// ── History ───────────────────────────────────────────────────────────────────

export interface RunHistorySummary {
  run_id: string
  completed_at: string
  run_status: string
  duration_seconds: number
  tracker_version: string
  notifications_sent: number
  total_watchlists: number
  succeeded: number
  failed: number
}

export interface HistoryResponse {
  runs: RunHistorySummary[]
  skipped_files: string[]
}

// ── System ────────────────────────────────────────────────────────────────────

export interface HealthCheckResult {
  status: 'ok' | 'error'
  detail: string | null
}

export interface HealthResponse {
  status: 'healthy' | 'unhealthy'
  checks: Record<string, HealthCheckResult>
}

export interface InfoResponse {
  api_version: string
  schema_version: number
  hostname: string
  run_in_progress: boolean
  tracker_version: string | null
  last_run_id: string | null
  last_run_status: string | null
  last_run_at: string | null
  commit_hash: string | null
  server_started_at: string
}

export interface SettingsResponse {
  run_timeout_seconds: number
  max_history_runs: number
  python_executable: string
  cors_origins: string[]
  tracker_script: string
  watchlist_file: string
  scheduler_enabled: boolean
  scheduler_min_interval_seconds: number
  scheduler_max_interval_seconds: number
  scheduler_quiet_hours_enabled: boolean
  scheduler_quiet_hours_start: string
  scheduler_quiet_hours_end: string
  scheduler_randomize_order: boolean
}

// ── Activity feed ─────────────────────────────────────────────────────────────

// Must stay in sync with ActivityEventType in web/models/activity.py.
export type ActivityEventType =
  | 'run_start'
  | 'watchlist_start'
  | 'watchlist_complete'
  | 'watchlist_blocked'
  | 'watchlist_failed'
  | 'watchlist_expiry_warning'
  | 'watchlist_expired'
  | 'watchlist_expiry_recovered'
  | 'notification_sent'
  | 'notification_failed'
  | 'run_complete'
  | 'run_cancelled'
  | 'scheduler_triggered'
  | 'scheduler_skipped'

export interface ActivityEvent {
  id: string
  timestamp: string
  event_type: ActivityEventType
  message: string
  payload: Record<string, unknown>
  run_id: string | null
}

export interface EventsResponse {
  events: ActivityEvent[]
  total: number
}

// ── Scheduler ─────────────────────────────────────────────────────────────────

export type SchedulerStatusValue = 'disabled' | 'scheduled' | 'quiet'

export interface SchedulerStatus {
  enabled: boolean
  status: SchedulerStatusValue
  last_triggered_at: string | null
  last_trigger_type: string | null
  next_run_at: string | null
  countdown_seconds: number | null
  min_interval_seconds: number
  max_interval_seconds: number
  quiet_hours_enabled: boolean
  quiet_hours_start: string
  quiet_hours_end: string
  randomize_order: boolean
}

// ── Run trigger ───────────────────────────────────────────────────────────────

export interface RunTriggerResponse {
  status: string
  message: string
}

// ── Job status (background run progress) ──────────────────────────────────────

export type JobStatusValue = 'idle' | 'starting' | 'running' | 'finished' | 'failed' | 'cancelled'

export interface JobStatus {
  status: JobStatusValue
  run_id: string | null
  started_at: string | null
  elapsed_seconds: number
  current_watchlist: string | null
  completed_watchlists: number
  total_watchlists: number
  error_message: string | null
  trigger_type: 'manual' | 'automatic'
}
