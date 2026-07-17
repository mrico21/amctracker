# AMCTracker — Handoff Document
**Session date:** 2026-07-17  
**Status:** Application polish complete. No files modified after this document.

---

## PROJECT STATUS

| Field | Value |
|---|---|
| **Version** | AMCTracker v1.0 |
| **Status** | Production Ready |
| **Current Focus** | Deployment and Daily Use |
| **Major Development** | Paused pending real-world feedback |

---

## 1. Current Project Status

The project is a household seat-availability tracker for AMC Theatres running on a Raspberry Pi. It consists of three independent layers:

1. **Tracker** (`tracker_multiwatch.py`) — production-stable Python CLI at v1.0.5
2. **Backend** (`web/`) — FastAPI REST API, all planned endpoints operational
3. **Frontend** (`web/frontend/`) — React PWA, scaffolded with a complete design system and four fully implemented pages (Dashboard, History, Run Details, Watchlists)

The frontend build is clean: `npm run build` produces 190 modules, zero TypeScript errors, a valid PWA service worker, and a `dist/` that FastAPI serves statically when present. All five pages (Dashboard, History, Run Details, Watchlists, Settings) are fully implemented and connected to all relevant backend APIs. The application is usable in production today.

All planned read-only frontend pages are complete. No placeholders remain. An application-wide polish pass has been completed: dark mode consistency, PWA safe area insets, dialog animations, accessibility focus rings, and visual consistency across all components.

---

## 2. Completed Milestones

### Tracker core — v1.0.5 (frozen)
- Multi-watchlist Playwright-based seat fetcher
- Three monitoring modes: `watch_seats`, `watch_any`, `watch_adjacent`
- Failure classification: `challenge_page`, `expired_url`, `parse_error`, `playwright_error`
- `--json-output PATH` writes schema_version 1 JSON after each run
- All CLI management flags (`--add`, `--edit`, `--clone`, `--enable`, `--disable`, `--remove`, `--inspect`, etc.)
- Loveseat auditorium support (`LoveSeatLeft`, `LoveSeatRight`)

### Backend — Milestone 2.1 Stabilization (complete)
- Fixed `FailureBreakdown` field names to match schema_version 1 exactly
- Fixed `WatchlistRunMonitoring` missing `Field(default_factory=list)` defaults
- Removed unused required field `TrackerRunRequest.request_id`

### Backend — Milestone 3 History API (complete)
- `GET /api/v1/history` → `HistoryResponse { runs: RunHistorySummary[], skipped_files: str[] }`
- `GET /api/v1/history/{run_id}` → full `RunResult`
- `HistoryService`: reads all UUID-named `.json` files from `runs_dir`, validates each with `RunResult.model_validate()`, sorts newest-first, caps at `max_history_runs`
- Corrupt/unreadable files are surfaced in `skipped_files`, never silently discarded

### Frontend — Scaffolding (complete)
- Vite 8 + React 19 + TypeScript (strict, `erasableSyntaxOnly`)
- Tailwind v4 with `@tailwindcss/vite`, no postcss.config or tailwind.config.ts needed
- `@custom-variant dark` + `.dark` class-based dark mode (controlled by ThemeProvider)
- React Router v7 with `createBrowserRouter`, 5 routes under `AppShell`
- TanStack Query v5 with 30s default stale time
- `vite-plugin-pwa` with full manifest, `autoUpdate` service worker
- Dev proxy: `/api` → `http://127.0.0.1:8000`
- `@/*` path alias mapped to `./src/`
- `web/main.py` conditionally mounts `StaticFiles("/")` when `frontend/dist/` exists
- `web/config/paths.py` has `frontend_dist: Path`

### Frontend — Application Polish (complete)

A targeted polish pass covering dark mode, PWA installation, dialog animation, accessibility, and visual consistency. No new features, no architectural changes, no new visual patterns. All changes used the existing design system.

**Dark mode fixes:**
- `Badge` `success` and `warning` variants were missing dark mode classes — added `dark:bg-emerald-900/30 dark:text-emerald-400` and `dark:bg-amber-900/30 dark:text-amber-400` respectively. These appeared washed-out in dark mode before.

**PWA / iOS safe area:**
- `index.css`: Added two `@utility` classes — `pb-safe` (`env(safe-area-inset-bottom, 0px)`) and `pb-nav-safe` (`calc(4rem + env(safe-area-inset-bottom, 0px))`) — for proper layout on iPhones with home indicator when installed as a PWA with `viewport-fit=cover`.
- `BottomNav`: Added `pb-safe` so the nav bar extends below the home indicator instead of clipping content.
- `AppShell` main: Changed `pb-16` to `pb-nav-safe` so page content clears both the BottomNav and the home indicator.

**Dialog animations (functional fix):**
- `ConfirmDialog` previously used `tailwindcss-animate` classes (`animate-in`, `animate-out`, `fade-out-0`, `zoom-in-95`, etc.) that do not exist in this project — the dialog opened/closed with no animation.
- Added four `@keyframes` in `index.css` (`dialog-overlay-in/out`, `dialog-content-in/out`) using CSS `scale` property (composites with `transform: translate`, no conflict).
- Updated `ConfirmDialog` to use `data-[state=open]:animate-[dialog-content-in_150ms_ease-out]` etc. via Tailwind v4 arbitrary animation values. Radix UI waits for `animationend` before unmounting, so close animations play correctly.

**Accessibility:**
- `RunDetails` back button: added `rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring` to the raw `<button>` — it had no visible focus indicator on keyboard navigation.
- `SkippedFilesWarning` expand/dismiss buttons: same focus-visible ring treatment.
- `CopyButton`: added `aria-label="Copy to clipboard"` alongside the existing `title` attribute for screen reader clarity.

**Visual consistency:**
- `WatchlistResultsList` (Dashboard): replaced hardcoded `CheckCircle`/`XCircle` icons with `StatusIcon` — now handles `partial_failure`, `running`, `skipped` states correctly and matches the rest of the app.
- `LatestRunCard` loading skeleton: replaced inline pulse divs with `Skeleton` component, consistent with all other skeleton usage.
- `RunProgressBanner`: changed `rounded-lg` → `rounded-xl` to match all other alert-style elements (`SkippedFilesWarning`, `FailureBreakdownCard`).
- Dashboard `triggerRun.isError` display: promoted from unstyled `<p>` to a proper bordered error callout with `AlertCircle` icon — consistent with `ErrorState` and `FailureBreakdownCard` patterns.

**Minor cleanup:**
- `StatCard`: removed empty string from `cn('', className)` → `cn(className)`.
- `SectionHeader` h2: added `tracking-tight` for consistency with AppHeader h1.
- `HealthCard` `CardContent`: removed redundant `pt-0` (already the default in `CardContent`).

---

### Frontend — Settings Page (complete)

**New: Settings feature** (`src/features/settings/index.tsx`):
- Loads `useSettings()` (primary, staleTime 300s) and `useInfo()` (supplementary app info)
- `useTheme()` provides live theme state — the one interactive setting on the page
- Error/loading early-return pattern matches all other pages
- Seven sections in order:
  1. **Appearance** — `Light / Dark / System` 3-button toggle using `Button` CVA variants (active = `default`, inactive = `outline`); `setTheme()` writes to localStorage via ThemeProvider. Responsive: stacked on mobile, inline on `sm+`.
  2. **Tracker** — `python_executable`, `tracker_script`, `watchlist_file` in monospace, `run_timeout_seconds` formatted as `"Ns"`. Rendered as a divided `Card` list using local `SettingRow` helper and Tailwind `divide-y`.
  3. **History** — `max_history_runs` plain number.
  4. **Network** — `cors_origins` rendered as monospace `Badge` pills (secondary variant).
  5. **Application** — `api_version`, `schema_version`, `tracker_version`, `hostname` from `useInfo()` (shown as "—" if info not yet loaded).
  6. **Notifications** (disabled placeholder) — `opacity-60` section with `Lock` icon + explanatory text.
  7. **Scheduling** (disabled placeholder) — same pattern, describes APScheduler as a future feature.
- Local helpers (not shared): `SettingRow` (label + value, optional `mono`), `PlaceholderSection` (locked placeholder card)
- No new shared components were needed — all composition uses existing `Card`, `CardContent`, `Button`, `Badge`, `SectionHeader`, `AppHeader`, `PageContainer`, `ErrorState`, `LoadingState`

**Updated: `src/pages/Settings.tsx`**: changed from placeholder to `export { default } from '@/features/settings'`

---

### Frontend — Watchlists Page (complete)

**`WatchlistCard` enhanced** (shared component, `src/components/common/WatchlistCard.tsx`):
- Added `latestResult?: WatchlistRunResult` optional prop — when provided, shows a `StatusBadge` from the last run in the card header (enabled watchlists only) and an availability summary (seat count, adjacent window count, notification pill)
- Added inline `MonitoringDetail` sub-component that renders badge pills for each configured monitoring mode: `watch_seats` (specific seat labels), `watch_any` (any-row), `watch_adjacent` (adjacent windows with row labels)
- Added `StatusBadge` import for last-run status display
- Added `Bell` icon for notification indicator
- Replaced the previous flat `monitoringModes` badge row with full configuration detail

**New: Watchlists feature** (`src/features/watchlists/index.tsx`):
- Loads `useWatchlists()` (primary) and `useLatestRun()` (supplementary, non-blocking)
- Error/loading/empty/populated states follow the established History page pattern
- Builds a `name → WatchlistRunResult` lookup map from the latest run; passed to each `WatchlistCard` as `latestResult` (undefined when no run data yet or name not present)
- `AppHeader` description: "N enabled · M total" (or "N watchlists" when all enabled)
- Empty state uses `Tv2` icon from lucide-react with CLI guidance text
- Watchlists render in their configured order (index order from backend)

**Updated: `src/pages/Watchlists.tsx`**: changed from placeholder to `export { default } from '@/features/watchlists'`

### Frontend — Run Details Page (complete)

**New shared components:**
- `src/components/common/RelativeTime.tsx` — `<time dateTime={iso} title={full date}>` wrapper; shows relative time with full datetime tooltip; supports null/undefined gracefully. Used by RunCard and Run Details timestamps.
- `src/components/common/StatusIcon.tsx` — maps status string (`success`, `failed`, `partial_failure`, `running`, `skipped`) to a colored lucide icon. Two sizes (`sm`/`md`). Used by WatchlistResultCard.

**`RunCard` updated** (shared component, `src/components/common/RunCard.tsx`):
- Replaced inline `formatRelativeTime` + `title={formatDateTime(...)}` with `<RelativeTime>` component
- Removed `formatDateTime` and `formatRelativeTime` from format imports (now internal to RelativeTime)

**New: Run Details feature** (`src/features/run-details/`):
- `RunSummaryStats.tsx` — 4-cell stat grid (Total/Succeeded/Failed/Notifications) using `StatCard`; color-coded values (emerald for good, destructive for failures)
- `FailureBreakdownCard.tsx` — amber-bordered card listing each non-zero failure type with count bubble, label, and description; returns `null` when no failures (no gap in layout)
- `WatchlistResultCard.tsx` — rich per-watchlist card showing: `StatusIcon` + name + `StatusBadge` + external link; monitoring config (specific seats, any-row, adjacent windows) as badge pills; seat/adjacent-window availability counts; notification sent indicator; failure type + error message for failed watchlists; disabled watchlists shown at 60% opacity with no body
- `index.tsx` — Run Details page: back button (← History), `AppHeader` with tracker version + hostname description, identity strip (status badge + truncated run ID + copy button + duration), timestamp grid (started/completed via `RelativeTime`), `RunSummaryStats`, conditional `FailureBreakdownCard`, `SectionHeader`-labeled watchlist list

**Updated: `src/pages/RunDetails.tsx`**: changed from placeholder to `export { default } from '@/features/run-details'`

### Frontend — History Page (complete)

**Bug fix:**
- `StatusCard.tsx`: removed `className` from `<CardContent>` (was applied to both outer `<Card>` and inner `<CardContent>`)

**`RunCard` enhanced** (shared component, `src/components/common/RunCard.tsx`):
- Added `CopyButton` for full `run_id` with `stopPropagation` wrapper to prevent accidental navigation
- Added `ChevronRight` icon with `group-hover:translate-x-0.5` animation as a navigation affordance
- Added `hover:shadow-md` lift effect and `transition-all duration-150` for polished card interaction
- Added `title={run.run_id}` tooltip on truncated UUID

**New: `SkippedFilesWarning`** (`src/features/history/components/SkippedFilesWarning.tsx`):
- Amber-toned dismissible inline warning banner
- Expandable "Show details" / "Hide details" toggle listing skipped filenames in monospace
- Scrollable file list (`max-h-40 overflow-y-auto`) handles many files gracefully
- Session-local dismiss (localStorage not used — hides until page refresh)
- Full dark mode support

**New: History page** (`src/features/history/index.tsx`):
- Three early-return states: error (`ErrorState` + retry), loading (`LoadingState`)
- Empty state: `EmptyState` with `Clock` icon and guidance to use the Dashboard
- Populated state: `AppHeader` with dynamic description ("N runs recorded"), optional `SkippedFilesWarning`, `RunCard` list in `space-y-2` grid
- All API access via `useHistory()` hook — no direct `apiClient` calls
- Follows Dashboard feature as canonical reference for structure and pattern

**Updated: `src/pages/History.tsx`**: changed from raw placeholder to `export { default } from '@/features/history'`

### Frontend — Design System + Dashboard (complete)

**Infrastructure:**
- `src/lib/queryKeys.ts` — centralized query key factory
- `src/lib/format.ts` — `formatRelativeTime`, `formatDuration`, `formatDateTime`, `truncateUuid`
- `src/providers/ThemeProvider.tsx` — light/dark/system, localStorage persistence, matchMedia listener, applies `.dark` to `<html>`
- `src/api/client.ts` — typed `apiClient` with `ApiError` class carrying `.status` for HTTP-aware error handling
- `src/api/types.ts` — full TypeScript interfaces mirroring all backend Pydantic models

**All 7 API hooks** (`src/hooks/`): `useInfo`, `useHealth`, `useLatestRun`, `useTriggerRun`, `useHistory`, `useWatchlists`, `useSettings`

**Shared components** (`src/components/`):
- `ui/`: `Button` (CVA variants), `Badge` (CVA variants), `Card/CardHeader/CardTitle/CardDescription/CardContent/CardFooter`, `Skeleton`
- `layout/`: `AppShell`, `Sidebar` (desktop, `w-64`, hidden on mobile), `BottomNav` (fixed bottom, hidden on desktop)
- `common/`: `AppHeader`, `PageContainer`, `SectionHeader`, `StatusBadge`, `StatusIcon`, `HealthIndicator`, `RelativeTime`, `LoadingState`, `EmptyState`, `ErrorState`, `StatCard`, `StatusCard`, `RunCard`, `WatchlistCard`, `CopyButton`, `ConfirmDialog`, `SkeletonCard`

**Dashboard feature** (`src/features/dashboard/`):
- `DashboardStats` — 4-cell grid: last run time, status badge, watchlist score, notification count
- `LatestRunCard` — run metadata, `WatchlistResultsList` (per-watchlist icon + seat count + notification bell), copy run ID, link to Run Details
- `HealthCard` — individual health check results, hostname, tracker version
- `RunProgressBanner` — animated blue banner while `run_in_progress` is true
- `useRunCompletion` — detects `true → false` transition on `run_in_progress`, auto-invalidates `latestRun` and `history` caches
- `Dashboard` page — `ConfirmDialog`-gated "Run Now" button, adaptive polling (5s running / 30s idle), full `ErrorState` fallback when backend is unreachable

---

## 3. Current Architecture

### Tracker (`C:\AMCTracker\tracker_multiwatch.py`)
Single-file Python CLI. Playwright fetches AMC seat pages headlessly. Seat data extracted from Next.js RSC payload via brace-balancing. State persisted in `state.json`. Notifications via Pushover. Run output written to `runs_dir` via `--json-output` flag. No web server dependency.

### Backend (`C:\AMCTracker\web\`)
```
web/
  main.py                    FastAPI app, CORS, lifespan, StaticFiles mount
  api/
    v1/
      __init__.py            Aggregated router
      health.py              GET /health
      info.py                GET /info
      runs.py                GET /run/latest, POST /run
      settings.py            GET /settings
      watchlists.py          GET /watchlists
      history.py             GET /history, GET /history/{run_id}
    dependencies.py          All FastAPI dependency providers
  config/
    paths.py                 ProjectPaths (all file system paths)
    exceptions.py            HistoryRunNotFoundError, RunOutputInvalidError
  models/
    run_result.py            RunResult + sub-models (frozen, extra="ignore")
    watchlist.py             WatchlistEntry, WatchlistAdjacentConfig
    settings.py              BackendSettings, SettingsUpdate, SettingsResponse
    health.py                HealthResponse, HealthCheckResult
    info.py                  InfoResponse
    history.py               RunHistorySummary, HistoryResponse
    tracker_run.py           TrackerRunRequest (frozen dataclass)
  services/
    history_service.py       HistoryService — read-only, validates all archived JSON on request
    health_service.py
    info_service.py
    run_service.py
    settings_service.py
    watchlist_service.py
    tracker_runner.py        Subprocess execution, async locking
  startup/
    watchlist_migration.py   Ensures all watchlist entries have UUIDs
```

**API base path:** `/api/v1`  
**Serving:** uvicorn, single process. In production: also serves `frontend/dist/` via StaticFiles.

### Frontend (`C:\AMCTracker\web\frontend\`)
```
src/
  api/
    client.ts                ApiError class + typed apiClient
    types.ts                 All TypeScript interfaces
  lib/
    queryKeys.ts             Centralized query key factory
    format.ts                formatRelativeTime, formatDuration, formatDateTime, truncateUuid
    utils.ts                 cn() utility
  hooks/                     All TanStack Query hooks — the only place apiClient is called
    useInfo.ts
    useHealth.ts
    useLatestRun.ts
    useTriggerRun.ts
    useHistory.ts
    useWatchlists.ts
    useSettings.ts
  providers/
    ThemeProvider.tsx        Theme context, localStorage, .dark class management
  components/
    ui/                      Primitive components (Button, Badge, Card, Skeleton)
    layout/                  AppShell, Sidebar, BottomNav
    common/                  17 shared app-level components (+ RelativeTime, StatusIcon)
  features/
    dashboard/
      components/            5 dashboard-specific sub-components
      hooks/                 useRunCompletion
      index.tsx              Dashboard page
    history/
      components/            SkippedFilesWarning
      index.tsx              History page
    run-details/
      components/            RunSummaryStats, FailureBreakdownCard, WatchlistResultCard
      index.tsx              Run Details page
    watchlists/
      index.tsx              Watchlists page
    settings/
      index.tsx              Settings page
  pages/                     Thin re-exports pointing into features/
    Dashboard.tsx            export { default } from '@/features/dashboard'
    History.tsx              export { default } from '@/features/history'
    RunDetails.tsx           export { default } from '@/features/run-details'
    Watchlists.tsx           export { default } from '@/features/watchlists'
    Settings.tsx             export { default } from '@/features/settings'
  App.tsx                    createBrowserRouter, 5 routes under AppShell
  main.tsx                   ThemeProvider > QueryClientProvider > App
  index.css                  Tailwind v4 import, @theme inline, .dark vars, @custom-variant
```

---

## 4. Remaining Roadmap (Priority Order)

### Frontend pages — ✅ All complete

| Page | Status |
|---|---|
| **Dashboard** | ✅ Complete |
| **History** | ✅ Complete |
| **Run Details** | ✅ Complete |
| **Watchlists** | ✅ Complete |
| **Settings** | ✅ Complete |

### Near-term — Backend gaps

| Priority | Feature | Notes |
|---|---|---|
| 1 | `PUT /api/v1/settings` | Enables Settings page save button (editable fields: `run_timeout_seconds`, `max_history_runs`) |
| 2 | Watchlist CRUD endpoints | `POST`, `PUT/{id}`, `DELETE/{id}` — enables Watchlists page editing |

### Future — Infrastructure

| Priority | Feature | Notes |
|---|---|---|
| 7 | APScheduler integration | Automatic scheduled runs without cron |
| 8 | Raspberry Pi deployment guide | Systemd service, nginx or direct uvicorn, startup on boot |
| 9 | Branded PWA icons | Replace solid-color placeholder PNGs |

---

## 5. Known Bugs

### Must Fix (before component sees first use)

*No outstanding must-fix bugs.*

### Nice to Have

**`StatCard` value API widened to `React.ReactNode`**
- File: `src/components/common/StatCard.tsx`
- Issue: `value` was widened from `string | number | null | undefined` to `React.ReactNode` to allow the Status stat in `DashboardStats` to pass a `<StatusBadge />`. A `StatusBadge` now renders inside a `text-2xl font-bold` span, which works visually but is architecturally awkward — a number card's value slot is holding a badge component.
- Impact: Low. Visual appearance is acceptable.
- Better fix (future): Add a `valueNode?: React.ReactNode` prop alongside the narrow `value` prop, or create a `StatusStatCard` variant.

---

## 6. Technical Debt

~~**`skipped_files` UI not yet designed**~~ ✅ Implemented — `SkippedFilesWarning` component in the History feature.

**No global error/toast system**
`useTriggerRun` mutation errors render as an inline red paragraph within the Dashboard page. If future pages need to surface mutation errors globally, a context-based notification system or a toast library will need to be introduced. This was deferred intentionally to keep the initial build lean.

**History page needs pagination consideration**
`useHistory` fetches all runs up to `max_history_runs` (default 50). At 50 entries this is fine. If `max_history_runs` is raised significantly, a virtualized list or pagination should be considered. Not blocking for v1.

**`useHistory` staleTime is 30 seconds**
After a run completes, `useRunCompletion` (Dashboard only) invalidates the history cache. Other pages that display history will not auto-refresh. For v1 this is acceptable — users navigate back to Dashboard to trigger runs.

---

## 7. Temporary Workarounds

**PWA icons are programmatically generated solid-color squares**
- Files: `public/icons/icon-192.png`, `public/icons/icon-512.png`, `public/icons/icon-180.png`
- These are valid PNG files (correct dimensions, correct format) generated by `make_icons.py` using pure Python `struct`/`zlib`. They are filled with the app's dark background color `(9, 9, 11)`.
- They satisfy the PWA manifest requirements and allow "Add to Home Screen" to function.
- They are not branded. Replace before presenting to users outside the household.

**`make_icons.py` left in the frontend root**
- File: `web/frontend/make_icons.py`
- Dev-only script used once to generate placeholder icons. Left in place rather than deleted. Should be moved to `scripts/` or removed before production.

**Vite template assets remain in `src/assets/`**
- Files: `src/assets/hero.png`, `src/assets/react.svg`, `src/assets/vite.svg`
- Carried over from the `npm create vite` template. Not imported by any current file. Dead weight.

---

## 8. Unused Files / Components

| File | Reason Unused | Safe to Delete? |
|---|---|---|
| `src/assets/hero.png` | Vite template | Yes — now |
| `src/assets/react.svg` | Vite template | Yes — now |
| `src/assets/vite.svg` | Vite template | Yes — now |
| `web/frontend/make_icons.py` | One-time icon generator | Yes — or move to `scripts/` |
| `src/components/common/StatusCard.tsx` | Built for future reuse; Dashboard uses custom layouts | No — keep (bug fixed) |
| `src/components/common/RunCard.tsx` | **Now used by History page** | N/A — in active use |
| `src/components/common/WatchlistCard.tsx` | **Now used by Watchlists page** | N/A — in active use |
| `src/components/common/SkeletonCard.tsx` | No page currently uses it — available for future use | No — keep |
| `src/hooks/useHistory.ts` | **Now used by History page**; `useHistoryRun` used by Run Details | N/A — in active use |
| `src/hooks/useWatchlists.ts` | **Now used by Watchlists page** | N/A — in active use |
| `src/hooks/useSettings.ts` | **Now used by Settings page** | N/A — in active use |

---

## 9. Recommended Cleanup

Perform these before continuing development. None are blocking — none touch logic.

1. **Delete Vite template assets:** `src/assets/hero.png`, `src/assets/react.svg`, `src/assets/vite.svg`
2. ~~**Fix `StatusCard` double-className bug**~~ ✅ Fixed in this session
3. **Move or delete `web/frontend/make_icons.py`** (move to `web/scripts/make_icons.py` or delete)

These items are the remaining recommended cleanup. Do not reorganize anything else.

---

## 10. Definition of Done — History Page ✅ Complete

All criteria satisfied:

- [x] Navigating to `/history` renders the History page (not the placeholder)
- [x] A `LoadingState` is shown while `useHistory` is fetching
- [x] When `runs` is empty, an `EmptyState` is shown with an appropriate message and icon
- [x] When `runs` is non-empty, every run is rendered as a `RunCard` in newest-first order
- [x] Clicking any `RunCard` navigates to `/history/{run_id}`
- [x] When `skipped_files.length > 0`, a dismissible amber banner appears with expandable "Show details" file list
- [x] When the query errors (backend unreachable), an `ErrorState` is shown with a retry button
- [x] `AppHeader` displays "History" as the page title with dynamic run count description
- [x] `PageContainer` wraps all content for consistent max-width and padding
- [x] No business logic lives directly in the page component
- [x] Feature code lives under `src/features/history/` with page exported from `src/features/history/index.tsx`
- [x] `src/pages/History.tsx` re-exports from `@/features/history`
- [x] `npm run build` passes with zero TypeScript errors (168 modules)
- [x] RunCard enhanced: CopyButton, ChevronRight affordance, hover shadow + translate animation, datetime tooltips

---

## 11. Definition of Done — Run Details Page (Next Milestone)

The Run Details page is complete when:

- [ ] Navigating to `/history/{run_id}` renders the Run Details page (not a placeholder)
- [ ] Run ID is extracted from the URL via `useParams`
- [ ] Data is fetched using `useHistoryRun(runId)` from `src/hooks/useHistory.ts`
- [ ] A `LoadingState` is shown while fetching
- [ ] When the query errors (404 or backend unreachable), an `ErrorState` is shown with a back link to `/history`
- [ ] `AppHeader` displays "Run Details" with a back button (← History) navigating to `/history`
- [ ] `PageContainer` wraps all content
- [ ] Top-level run metadata shown: `run_id` (with `CopyButton`), `started_at`, `completed_at`, `duration_seconds` (formatted), `run_status` (`StatusBadge`), `tracker_version`, `hostname`
- [ ] Per-watchlist breakdown renders every `WatchlistRunResult`: name, enabled status, status (`StatusBadge`), `seats_available`, `notification_sent`, `failure_type` and `error_message` if failed
- [ ] If `failure_breakdown` has non-zero counts, a summary section shows which failure types occurred
- [x] Navigating to `/history/{run_id}` renders the Run Details page
- [x] Run ID extracted from URL via `useParams`
- [x] Data fetched via `useHistoryRun(runId)` from `src/hooks/useHistory.ts`
- [x] Loading state shown while fetching
- [x] Error state with back link to `/history` when query fails
- [x] Back button (← History) at top of page
- [x] `AppHeader` with tracker version + hostname as description
- [x] Identity strip: `StatusBadge`, truncated `run_id` with `CopyButton`, formatted duration
- [x] Timestamp grid: Started / Completed via `RelativeTime` (full datetime in tooltip)
- [x] 4-stat grid: Total, Succeeded, Failed, Notifications (`RunSummaryStats`)
- [x] `FailureBreakdownCard` — returns null when no failures, shows count + description per type when present
- [x] Per-watchlist `WatchlistResultCard` with: `StatusIcon`, `StatusBadge`, monitoring config badges, seat/adjacent counts, notification pill, failure error box
- [x] Feature code under `src/features/run-details/index.tsx`
- [x] `src/pages/RunDetails.tsx` re-exports from `@/features/run-details`
- [x] `npm run build` passes with zero TypeScript errors (178 modules)
- [x] New shared components: `RelativeTime`, `StatusIcon`

---

## 12. Definition of Done — Watchlists Page ✅ Complete

All criteria satisfied:

- [x] Navigating to `/watchlists` renders the Watchlists page (not the placeholder)
- [x] Data is fetched using `useWatchlists()` from `src/hooks/useWatchlists.ts`
- [x] `useLatestRun()` loaded supplementarily for availability cross-reference (non-blocking)
- [x] A `LoadingState` is shown while fetching
- [x] When the query errors, an `ErrorState` is shown with a retry button
- [x] When `watchlists` is empty, an `EmptyState` is shown (`Tv2` icon, CLI guidance)
- [x] When populated, each `WatchlistEntry` is rendered as an enhanced `WatchlistCard`
- [x] `AppHeader` shows "Watchlists" with "N enabled · M total" or "N watchlists" description
- [x] `PageContainer` wraps all content
- [x] Disabled watchlists shown at 60% opacity with "Disabled" badge; no body content shown
- [x] `WatchlistCard` enhanced: monitoring config badge pills (specific seats, any-row, adjacent), `StatusBadge` from latest run, availability summary (seat count, adjacent windows, notification pill)
- [x] Feature code under `src/features/watchlists/index.tsx`
- [x] `src/pages/Watchlists.tsx` re-exports from `@/features/watchlists`
- [x] `npm run build` passes with zero TypeScript errors (183 modules)

---

## 13. Definition of Done — Settings Page ✅ Complete

All criteria satisfied:

- [x] Navigating to `/settings` renders the Settings page (not the placeholder)
- [x] Data is fetched using `useSettings()` from `src/hooks/useSettings.ts`
- [x] A `LoadingState` is shown while fetching
- [x] When the query errors, an `ErrorState` is shown with a retry button
- [x] All `SettingsResponse` fields displayed read-only:
  - `run_timeout_seconds` — rendered as "Ns"
  - `max_history_runs` — plain number
  - `python_executable` — monospace path
  - `cors_origins` — monospace `Badge` pills
  - `tracker_script` — monospace path
  - `watchlist_file` — monospace path
- [x] `useInfo()` supplementary data displayed: `api_version`, `schema_version`, `tracker_version`, `hostname`
- [x] Theme selector (Light / Dark / System) fully interactive via `useTheme()` / `setTheme()`
- [x] Notifications and Scheduling shown as disabled placeholders (`opacity-60`, `Lock` icon)
- [x] `AppHeader` shows "Settings" with description
- [x] `PageContainer` wraps all content
- [x] Feature code under `src/features/settings/index.tsx`
- [x] `src/pages/Settings.tsx` re-exports from `@/features/settings`
- [x] `npm run build` passes with zero TypeScript errors (189 modules)

---

## ARCHITECTURE FREEZE

The following principles are locked. Do not deviate without explicit user instruction.

- **The tracker (`tracker_multiwatch.py`) is production-stable.** Do not modify it unless fixing a confirmed bug. Schema_version 1 JSON output is frozen — no new fields, no renamed fields.
- **The schema_version 1 JSON contract is frozen.** The backend models in `web/models/run_result.py` conform to it exactly. Do not change field names or types.
- **The FastAPI architecture is frozen.** Router structure, dependency injection pattern, service layer, path prefixes, and response model conventions are established. Do not reorganize.
- **The React architecture is frozen.** The `src/` directory structure (api/, lib/, hooks/, providers/, components/, features/, pages/) is the final layout. Do not move, rename, or restructure folders.
- **Feature folder organization is frozen.** New pages live at `src/features/{name}/index.tsx`. Sub-components live at `src/features/{name}/components/`. Page-specific hooks live at `src/features/{name}/hooks/`. `src/pages/{Name}.tsx` re-exports from the feature.
- **All API access must remain inside custom hooks.** `apiClient` is never called directly in a page component or a shared component. If a component needs data, it calls a hook.
- **Pages must never import from `src/api/client.ts` directly.** The only valid importers of `apiClient` are files in `src/hooks/`.
- **TanStack Query is the single data-fetching layer.** Do not use `useEffect` + `fetch`, SWR, or any other mechanism for server state.
- **Shared components should always be preferred over page-specific implementations.** Before building a new component inside a feature folder, check whether an equivalent already exists in `src/components/common/`. Extend an existing component before creating a new one.
- **Do not reorganize folders or rename components unless fixing a confirmed bug.** The existing names and locations were deliberate. Refactoring for its own sake is prohibited.

---

## CURRENT TECH STACK

### Tracker
| Library | Version | Role |
|---|---|---|
| Python | 3.x | Runtime |
| Playwright | latest | Headless Chromium, AMC seat page fetching |
| requests | latest | Pushover HTTP notifications |

### Backend
| Library | Version | Role |
|---|---|---|
| Python | 3.x | Runtime |
| FastAPI | latest | REST API framework |
| Pydantic v2 | latest | Request/response models, validation |
| uvicorn | latest | ASGI server |
| starlette | (via FastAPI) | StaticFiles, middleware |

### Frontend
| Library | Version | Role |
|---|---|---|
| React | 19 | UI framework |
| TypeScript | latest | Type system (`erasableSyntaxOnly`, strict) |
| Vite | 8 | Build tool, dev server |
| `@vitejs/plugin-react` | latest | React fast refresh |
| Tailwind CSS | 4.3.2 | Utility-first CSS, `@theme inline` CSS variables |
| `@tailwindcss/vite` | 4.3.2 | Vite plugin (no postcss.config needed) |
| React Router | 7.18.1 | Client-side routing, `createBrowserRouter` |
| TanStack Query | 5.101.2 | Server state, caching, polling, mutations |
| `vite-plugin-pwa` | 1.3.0 | PWA manifest, service worker generation |
| lucide-react | latest | All icons (the only icon library in use) |
| clsx | latest | Conditional class name joining |
| tailwind-merge | latest | Tailwind class conflict resolution |
| class-variance-authority | latest | CVA variant definitions for Button/Badge |
| `@radix-ui/react-slot` | latest | `asChild` prop pattern for Button |
| `@radix-ui/react-dialog` | latest | Accessible modal for ConfirmDialog |

---

## UI DESIGN PRINCIPLES

- **Mobile-first.** Every component is designed for 375px and scales up. Desktop layouts use responsive grid/flex breakpoints (`md:`).
- **Responsive.** Navigation switches between BottomNav (mobile) and Sidebar (desktop) at the `md` breakpoint. Content grids adapt column count.
- **Clean.** Minimal visual noise. No decorative borders, shadows only where they aid depth (cards). Generous whitespace.
- **Modern.** Zinc/slate color palette in oklch. System font stack. No gradients in UI chrome.
- **Apple-quality polish.** Transitions are fast (150ms). Interactive elements have clear hover/active states. Focus rings follow accessibility standards. Bottom nav uses safe area insets for iPhone notch handling.
- **Consistent spacing.** PageContainer enforces `p-6` on all pages. Cards use `p-4` or `p-6` uniformly. Gap between sections is always `space-y-6` within PageContainer.
- **Minimal animations.** Only purposeful animation: spinner for loading, pulse for skeleton, run progress banner. No gratuitous entrance animations.
- **Reuse shared components whenever possible.** When building a new page, reach for `AppHeader`, `PageContainer`, `SectionHeader`, `LoadingState`, `EmptyState`, `ErrorState`, `StatusBadge`, `StatCard`, `RunCard`, `WatchlistCard`, `CopyButton`, `SkeletonCard` before writing new markup.

---

## NEXT SESSION START PROMPT

```
You are continuing development on AMCTracker — a seat availability tracker
for AMC Theatres, built as a household tool running on a Raspberry Pi.

Project root: C:\AMCTracker

═══════════════════════════════════════════
PROJECT OVERVIEW
═══════════════════════════════════════════

The project has three layers:

1. TRACKER: tracker_multiwatch.py (v1.0.5) — production-stable Python CLI.
   Do NOT modify it unless fixing a confirmed bug.

2. BACKEND: C:\AMCTracker\web\ — FastAPI REST API.
   All planned read-only endpoints are operational. Architecture is frozen.

3. FRONTEND: C:\AMCTracker\web\frontend\ — React PWA.
   Vite 8 + React 19 + TypeScript + Tailwind v4 + TanStack Query v5
   + React Router v7 + vite-plugin-pwa.
   Build passes: 190 modules, 0 TypeScript errors.
   ALL five pages are fully implemented:
   Dashboard, History, Run Details, Watchlists, Settings.
   No placeholders remain.

═══════════════════════════════════════════
READ THESE FILES FIRST — DO NOT SKIP
═══════════════════════════════════════════

Read in this order before proposing anything:

  CLAUDE.md
  PROJECT_HANDOFF.md
  web/frontend/src/api/types.ts
  web/frontend/src/api/client.ts
  web/models/settings.py                        <- check current backend fields
  web/api/v1/settings.py                        <- confirm GET/PUT endpoints

═══════════════════════════════════════════
ARCHITECTURE RULES (FROZEN — DO NOT DEVIATE)
═══════════════════════════════════════════

1. All API access lives in src/hooks/ only. Pages and components never
   import from src/api/client.ts directly.

2. All TanStack Query keys come from src/lib/queryKeys.ts.
   Do not hardcode query key strings anywhere else.

3. TanStack Query is the only data-fetching layer.
   No useEffect+fetch, no SWR, no alternatives.

4. Shared components in src/components/common/ are always preferred over
   writing equivalent markup inside a feature. Check there first.

5. Do not move, rename, or reorganize any existing files or folders.
   The directory structure is frozen.

6. The FastAPI architecture is frozen — do not reorganize routers or services.

═══════════════════════════════════════════
CURRENT STATE: ALL FRONTEND PAGES COMPLETE
═══════════════════════════════════════════

All five read-only pages are done. The next work is backend:

PRIORITY 1 — PUT /api/v1/settings
  Add a PUT endpoint so the Settings page can save changes to
  run_timeout_seconds and max_history_runs. Then wire up the
  Settings page with editable fields + save button.

PRIORITY 2 — Watchlist CRUD endpoints
  POST /api/v1/watchlists
  PUT  /api/v1/watchlists/{id}
  DELETE /api/v1/watchlists/{id}
  Then wire up the Watchlists page with add/edit/delete UI.

DO NOT start either of these without explicit user approval.
Present a plan first and wait for the go-ahead.

═══════════════════════════════════════════
WHAT NOT TO DO
═══════════════════════════════════════════

- Do NOT add new npm packages without a strong reason.
- Do NOT refactor or rename any existing files.
- Do NOT modify tracker_multiwatch.py.
- Do NOT add a toast library or global notification system
  (useTriggerRun errors are inline; this is acceptable for v1).
- Do NOT delete unused assets (hero.png, etc.) — lower priority.
- Do NOT start the backend or dev server unless asked.
```
