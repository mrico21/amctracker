# AMCTracker Release Notes

---

## v1.0.5 — 2026-06-29

Machine-readable JSON run summary via `--json-output PATH`. Schema version 1 is frozen as of this release.

---

### `--json-output PATH`

A new optional CLI flag that writes a complete, versioned JSON run summary to the specified path after each tracking run. This is the stable API contract between the tracker engine and future services (e.g., a FastAPI web backend on Raspberry Pi).

**Usage:**
```powershell
py tracker_multiwatch.py --json-output C:\AMCTracker\run_summary.json
```

The file is written after `state.json` is saved and the console run summary is printed. A write failure is caught, logged at WARNING, and never crashes the tracker. Console output and notifications are completely unchanged.

---

### JSON Schema (schema_version 1)

All timestamps are UTC with timezone offset. The internal failure classification constants (`CHALLENGE_PAGE`, `EXPIRED_URL`, etc.) are normalized to `lower_snake_case` in the JSON; console and log output retain the uppercase form.

#### Successful run

```json
{
  "schema_version": 1,
  "generated_by": "AMCTracker",
  "generated_at": "2026-06-29T18:32:02.114853+00:00",
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "started_at": "2026-06-29T18:31:50.223401+00:00",
  "completed_at": "2026-06-29T18:32:01.988762+00:00",
  "duration_seconds": 11.765,
  "tracker_version": "1.0.5",
  "hostname": "DESKTOP-ABC123",
  "run_status": "success",
  "summary": {
    "total_watchlists": 2,
    "succeeded": 2,
    "disabled": 0,
    "failed": 0,
    "notifications_sent": 1,
    "cache_hits": 1,
    "cache_misses": 1
  },
  "failure_breakdown": {
    "challenge_pages": 0,
    "expired_urls": 0,
    "parse_errors": 0,
    "playwright_errors": 0
  },
  "watchlists": [
    {
      "name": "The Odyssey - Wed Jul 22 7:00pm",
      "enabled": true,
      "showtime_url": "https://www.amctheatres.com/showtimes/143822631/seats",
      "monitoring": {
        "watch_seats": ["J15", "J16", "J17"],
        "watch_adjacent": [{"rows": ["I", "J", "K", "L"], "count": 2}]
      },
      "status": "success",
      "seats_available": 1,
      "adjacent_windows_available": 3,
      "notification_sent": true,
      "failure_type": null,
      "error_message": null
    },
    {
      "name": "The Odyssey - Wed Jul 22 9:30pm",
      "enabled": true,
      "showtime_url": "https://www.amctheatres.com/showtimes/143822631/seats",
      "monitoring": {
        "watch_any": ["J13", "J14", "J15", "J16", "J17", "J18", "J19"]
      },
      "status": "success",
      "seats_available": 0,
      "adjacent_windows_available": 0,
      "notification_sent": false,
      "failure_type": null,
      "error_message": null
    }
  ]
}
```

#### Partial failure (one disabled, one succeeded, one failed)

```json
{
  "schema_version": 1,
  "generated_by": "AMCTracker",
  "generated_at": "2026-06-29T18:05:44.330120+00:00",
  "run_id": "b9c8d7e6-f5a4-3210-fedc-ba9876543210",
  "started_at": "2026-06-29T18:05:30.001002+00:00",
  "completed_at": "2026-06-29T18:05:44.118844+00:00",
  "duration_seconds": 14.118,
  "tracker_version": "1.0.5",
  "hostname": "DESKTOP-ABC123",
  "run_status": "partial_failure",
  "summary": {
    "total_watchlists": 3,
    "succeeded": 1,
    "disabled": 1,
    "failed": 1,
    "notifications_sent": 0,
    "cache_hits": 0,
    "cache_misses": 1
  },
  "failure_breakdown": {
    "challenge_pages": 1,
    "expired_urls": 0,
    "parse_errors": 0,
    "playwright_errors": 0
  },
  "watchlists": [
    {
      "name": "The Odyssey - Wed Jul 22 7:00pm",
      "enabled": false,
      "showtime_url": "https://www.amctheatres.com/showtimes/143822631/seats",
      "monitoring": {
        "watch_seats": ["J15", "J16", "J17"]
      },
      "status": "skipped",
      "seats_available": 0,
      "adjacent_windows_available": 0,
      "notification_sent": false,
      "failure_type": null,
      "error_message": null
    },
    {
      "name": "Inside Out 3 - Sat Jul 26 2:15pm",
      "enabled": true,
      "showtime_url": "https://www.amctheatres.com/showtimes/154901234/seats",
      "monitoring": {
        "watch_adjacent": [{"rows": ["G", "H", "I"], "count": 3}]
      },
      "status": "success",
      "seats_available": 0,
      "adjacent_windows_available": 0,
      "notification_sent": false,
      "failure_type": null,
      "error_message": null
    },
    {
      "name": "The Odyssey - Thu Jul 23 7:00pm",
      "enabled": true,
      "showtime_url": "https://www.amctheatres.com/showtimes/143855892/seats",
      "monitoring": {
        "watch_seats": ["H10", "H11"],
        "watch_any": ["H8", "H9", "H10", "H11", "H12"]
      },
      "status": "failed",
      "seats_available": 0,
      "adjacent_windows_available": 0,
      "notification_sent": false,
      "failure_type": "challenge_page",
      "error_message": "page received (7,318 chars) is too small for a valid seat map -- Cloudflare or rate-limit block"
    }
  ]
}
```

#### Full failure (every enabled watchlist failed)

```json
{
  "schema_version": 1,
  "generated_by": "AMCTracker",
  "generated_at": "2026-06-29T22:14:13.445901+00:00",
  "run_id": "deadbeef-0000-4000-8000-112233445566",
  "started_at": "2026-06-29T22:12:13.002101+00:00",
  "completed_at": "2026-06-29T22:14:13.208744+00:00",
  "duration_seconds": 120.207,
  "tracker_version": "1.0.5",
  "hostname": "DESKTOP-ABC123",
  "run_status": "failed",
  "summary": {
    "total_watchlists": 1,
    "succeeded": 0,
    "disabled": 0,
    "failed": 1,
    "notifications_sent": 0,
    "cache_hits": 0,
    "cache_misses": 0
  },
  "failure_breakdown": {
    "challenge_pages": 0,
    "expired_urls": 0,
    "parse_errors": 0,
    "playwright_errors": 1
  },
  "watchlists": [
    {
      "name": "The Odyssey - Wed Jul 22 7:00pm",
      "enabled": true,
      "showtime_url": "https://www.amctheatres.com/showtimes/143822631/seats",
      "monitoring": {
        "watch_seats": ["J15", "J16"],
        "watch_adjacent": [{"rows": ["I", "J", "K"], "count": 2}]
      },
      "status": "failed",
      "seats_available": 0,
      "adjacent_windows_available": 0,
      "notification_sent": false,
      "failure_type": "playwright_error",
      "error_message": "page.goto: Timeout 120000ms exceeded."
    }
  ]
}
```

---

### Schema contract (v1, frozen)

- `schema_version` increments only on breaking changes; additions of new optional fields are non-breaking
- `monitoring` object only includes keys present in the watchlist config; absent monitoring types are omitted entirely
- `run_status`: `"success"` (0 failed), `"partial_failure"` (some failed and some succeeded), `"failed"` (every enabled watchlist failed)
- Per-watchlist `status`: `"success"`, `"skipped"` (enabled=false in config), `"failed"`
- `failure_type` values: `"challenge_page"`, `"expired_url"`, `"parse_error"`, `"playwright_error"`, or `null`
- `run_id` is UUID v4, unique per invocation
- All timestamps are UTC ISO 8601 with `+00:00` offset

---

## v1.0.4 — 2026-06-12

Fetch failure classification — distinguishes transient bot-protection blocks from permanent showtime expiry, parse failures, and infrastructure errors.

---

### Failure Classification

Previously, all per-watchlist errors produced the same output regardless of cause:

```
[ERROR] The Odyssey - Wed Jul 22: seatingLayout not found in page source
```

Errors are now classified into four distinct categories using HTML size and seatingLayout presence as the primary signals. No vendor-specific strings are used.

#### CHALLENGE_PAGE

```
[CHALLENGE_PAGE] The Odyssey - Wed Jul 22: page received (7,318 chars) is too small for a valid seat map -- Cloudflare or rate-limit block
```

The fetched page is smaller than `_SMALL_PAGE_THRESHOLD` (200,000 chars). Confirmed Cloudflare Error 1015 ("You are being rate limited") pages are ~7KB; the smallest confirmed real AMC seat page is ~944KB — a 129x margin. This failure is transient; the tracker will likely succeed on the next scheduled run. Logged at WARNING (no stack trace).

#### EXPIRED_URL

```
[EXPIRED_URL] The Odyssey - Wed Jul 22: full page received (987,432 chars) but seatingLayout is absent -- showtime may be expired or URL is invalid
```

A full-sized page loaded but contains no seatingLayout. The showtime URL may point to an expired or removed showtime. Logged at WARNING (no stack trace).

#### PARSE_ERROR

```
[PARSE_ERROR] The Odyssey - Wed Jul 22: seatingLayout found but could not be parsed -- possible AMC page structure change; Expecting value: line 1 column 1 (char 0)
```

seatingLayout was found in a full-sized page but JSON extraction failed. This indicates an AMC page structure change that may require updating the extraction logic. Logged at EXCEPTION with full stack trace.

#### PLAYWRIGHT_ERROR

```
[PLAYWRIGHT_ERROR] The Odyssey - Wed Jul 22: page.goto: Timeout 120000ms exceeded.
```

An exception originated inside `fetch_html()` or Playwright infrastructure — browser launch failure, navigation timeout, OS-level error, etc. Logged at EXCEPTION with full stack trace.

---

### Run Summary Breakdown

The run summary now shows a per-category breakdown when any watchlist failed:

```
## Run Summary
Watchlists processed : 4
  Enabled            : 3
  Disabled skipped   : 0
  Failed             : 1
    Challenge/bot    : 1
    Expired URL      : 0
    Parse error      : 0
    Playwright error : 0
Unique URLs          : 4
Cache hits           : 0
Cache misses         : 4
Notifications sent   : 0
Duration             : 25.08 sec
```

When `Failed: 0`, the sub-breakdown is suppressed and the summary is identical to previous versions.

The `RUN SUMMARY` log line always includes all four sub-counts:
```
RUN SUMMARY | processed=3 skipped=0 failed=1 challenge=1 expired=0 parse=0 playwright=0 unique_urls=4 ...
```

---

### Implementation Notes

- New constant: `_SMALL_PAGE_THRESHOLD = 200_000`
- New function: `classify_page_failure(html: str, exc: Exception) -> str`
- `html = ""` initialized before each per-watchlist `try:` block; ensures the classifier can always reference `html` even if `fetch_html()` raised before returning
- No changes to success path, notification logic, state.json handling, or watchlist.json handling

---

## v1.0.3 — 2026-06-07

Seat entry improvements, loveseat theater support, and hydration reliability fix.

---

### LoveSeat Theater Support

AMC auditoriums using loveseat configurations type their seats as `LoveSeatLeft` and `LoveSeatRight` rather than `CanReserve`. The previous availability filter (`type == "CanReserve"`) excluded these seats entirely, causing the tracker to report zero available seats in loveseat theaters even when dozens were visible in the AMC UI.

Current reservable seat types:

- `CanReserve`
- `LoveSeatLeft`
- `LoveSeatRight`

These are the reservable seat types currently recognized by the tracker. Additional AMC auditorium-specific seat types may exist and may be added to `RESERVABLE_TYPES` in future versions after validation. Any type not present in `RESERVABLE_TYPES` is treated as non-reservable by default.

All availability checks — seat status tracking, `watch_any`, `watch_adjacent` window detection, `--inspect`, and `--list-seats` — now use `type in RESERVABLE_TYPES` instead of `type == "CanReserve"`.

`Wheelchair` and `Companion` seat types remain excluded from all availability counts in all contexts.

**Validation (live showtime — Scary Movie June 10 10:30 PM):**

Before:
- Available seats reported: 4
- Matching watch_adjacent windows: 0

After:
- Available seats reported: 63
- Matching watch_adjacent windows: 9

End-to-end verification:
- `--inspect` reported 63 reservable seats
- 9 matching `watch_adjacent` windows were detected
- Production tracker generated a notification
- Pushover notification was successfully received

---

### Hydration Reliability Improvements

The previous page load sequence used a fixed 8-second wait after navigation:

```
page.goto(url, timeout=120_000)
page.wait_for_timeout(8_000)
page.content()
```

AMC delivers seat data as streamed Next.js RSC chunks embedded inline in the HTTP response. On slower connections or when the AMC server was slow to stream, the 8-second wait captured only a partial payload — producing a truncated seat map with far fewer seats and available counts than the actual showtime.

The wait is now condition-based:

```
page.goto(url, timeout=120_000)
try:
    page.wait_for_load_state("networkidle", timeout=15_000)
except PlaywrightTimeoutError:
    page.wait_for_timeout(12_000)
page.content()
```

`networkidle` fires when no network connections have been active for 500ms, which reliably signals that RSC streaming has completed. If `networkidle` never fires — for example, due to analytics scripts making continuous requests — the fallback 12-second wait activates. Worst-case behavior is the same as the previous implementation; the primary path eliminates partial payload captures.

---

### New Diagnostic: --diagnose-seat-types

```
py tracker_multiwatch.py --diagnose-seat-types INDEX
```

Fetches the live seat map for the watchlist at INDEX and reports:

- **First 20 seat objects** — name, available, and type for each
- **Counts by (type, available)** — full breakdown of every type present in the layout
- **Filter comparison** — counts for `available is True`, `available == True`, `type == CanReserve`, and the production filter (`type in RESERVABLE_TYPES`)

Use this when `--inspect` shows fewer available seats than the AMC UI, or when configuring a watchlist for an unfamiliar auditorium. Read-only — no state changes, no notifications.

---

### Seat Range Expansion

`--add` and `--edit` now accept seat ranges for `watch_seats` and `watch_any`. Instead of listing every seat individually, enter a range in `ROW#-ROW#` form:

```
J1-J29          -> J1, J2, J3, ... J29
K10-K15         -> K10, K11, K12, K13, K14, K15
J1-J5,K10       -> J1, J2, J3, J4, J5, K10
```

Ranges are expanded to individual seat names before saving. `watchlist.json` always stores the full explicit list — existing files are unaffected.

**Validation:**
- Both sides must share the same row letter — `J5-K10` is rejected (cross-row)
- Start number must be <= end — `J10-J5` is rejected (descending)
- Tokens must match `ROW#` or `ROW#-ROW#` — `J1-5` is rejected (malformed)

Invalid input re-prompts; no partial saves occur.

---

### Monitor Mode Selection in --add

`--add` now prompts for monitor mode before collecting seat or row data:

```
Monitor mode:
  1. watch_seats
  2. watch_any
  3. watch_adjacent

Selection [1]:
```

Press Enter to select `watch_seats` (default). Type `2` for `watch_any` or `3` for `watch_adjacent`.

**watch_seats and watch_any** use the existing seat prompt. The selected key determines how the entry is saved. Seat range expansion (`J1-J5`) applies to both.

**watch_adjacent** prompts for rows and count:

- **Rows** — accepts a range (`G-L`), comma-separated letters (`G,H,I`), a single letter (`J`), or mixed (`G-L,N`). Ranges expand to individual letters before saving. Blank input re-prompts.
- **Count** — any integer >= 2. Press Enter to accept the default of `2`. Invalid input re-prompts.

Descending row ranges (`L-G`) and multi-character tokens (`AB`) are rejected; the prompt re-displays for correction.

---

### watch_adjacent Editing in --edit

`--edit` now interactively edits `watch_adjacent` entries when a watchlist has them configured. Two prompts are shown per config entry — rows and count — each defaulting to the current value (press Enter to keep).

**Row input** accepts three formats:

```
H-K        ->  H, I, J, K      (range)
H,I,J,K    ->  H, I, J, K      (comma-separated)
J          ->  J                (single letter)
H-K,M      ->  H, I, J, K, M   (mixed)
```

Row ranges expand to individual letters before saving. Descending ranges (`K-H`) and multi-character tokens (`AB`) are rejected; the prompt re-displays for correction.

**Count input** accepts any integer >= 2. Invalid input re-prompts.

If a watchlist has multiple `watch_adjacent` config entries, each is prompted in sequence, labeled `1 of N` / `2 of N`. If `watch_adjacent` is absent, the prompts are skipped entirely.

**Validation fix:** Watchlists that use only `watch_adjacent` (no `watch_seats` or `watch_any`) now correctly pass the monitoring-mode check during `--edit`. Previously, editing any field on such a watchlist would abort with an error.

---

### Clone Summary: All Monitoring Modes

`--clone` now displays all monitoring modes present in the source watchlist — both before prompting for the new name and URL, and in the post-clone confirmation.

**Pre-clone display:**
```
Cloning: The Odyssey - Wed Jul 22
  watch_seats : J15, J16, J17
  watch_any   : J13, J14, J15, J16, J17, J18, J19
  watch_adjacent:
    Rows  : I, J, K, L, M
    Count : 2
```

**Post-clone summary:**
```
Clone created successfully
Source : The Odyssey - Wed Jul 22
New    : The Odyssey - Thu Jul 23
URL    : https://www.amctheatres.com/showtimes/143822631/seats

watch_seats:
J15, J16, J17

watch_any:
J13, J14, J15, J16, J17, J18, J19

watch_adjacent:
Rows  : I, J, K, L, M
Count : 2
```

Watchlists using only `watch_adjacent` display correctly in both summaries. No clone behavior, schema, or state changes.

---

## v1.0.2 — 2026-06-07

Adjacent seat monitoring and display improvements.

---

### watch_adjacent

Monitor adjacent seat availability without manually listing every pair. Each `watch_adjacent` entry specifies a list of rows and a window size (`count`). The tracker discovers all seats in those rows from the live seat map and checks every consecutive window of `count` seats. A Pushover notification is sent when any window transitions to fully available.

```json
"watch_adjacent": [
  {
    "rows": ["I", "J", "K", "L", "M"],
    "count": 2
  }
]
```

**Notification:**
- Title: `AMC Seat Alert — {watchlist name}`
- Message: `Adjacent seats available:\n\n{window}\n{window}\n{url}`
- All newly-available windows batched into one message per run

**State:** Windows are stored under `adj:{seat1}-{seat2}` keys in `state.json`. Re-notification is suppressed for windows that remain available across runs.

`count` defaults to `2`. Any value >= 2 is supported without schema changes. A watchlist may use `watch_adjacent` alone, or alongside `watch_seats` and `watch_any`. Rows with no seats in the live seat map are silently skipped.

### --show-watchlists: watch_adjacent display

`--show-watchlists` now includes the `watch_adjacent` configuration for each watchlist entry, showing the configured rows and count for every entry.

### --inspect

Diagnose seat detection for any watchlist without affecting state. Accepts a 1-based index (from `--show-watchlists`), fetches the live seat map, and prints:

- **Seat map** — total seats discovered and total available CanReserve seats
- **All available seats** — every currently available seat with type
- **Adjacent windows (all rows)** — every consecutive N-seat window that is fully available, scanning all rows in the layout; N is taken from the first `watch_adjacent` count (default 2)
- **Matching watchlist criteria** — available windows per `watch_adjacent` config entry (filtered to configured rows); `watch_seats` and `watch_any` availability
- **Summary** — available seat count, total available windows (all rows), windows matching configured criteria

No state changes. No notifications. No file writes.

```
py tracker_multiwatch.py --inspect 1
```

---

## v1.0.1 — 2026-06-07

Reliability and robustness improvements.

---

### Exception Isolation

Each watchlist in the main tracking loop is wrapped in an independent `try/except` block. An error in one watchlist — page load failure, extraction error, or unexpected data — is caught, printed to the console, and logged without interrupting the remaining watchlists. A `Failed` counter in the run summary tracks how many watchlists errored during the run.

### Atomic State Writes

`save_state()` now writes to a temporary file (`state.json.tmp`) and atomically renames it to `state.json` on completion. If the process is killed during a write, `state.json` remains intact from the previous run. The temporary file is safe to delete if found.

### --test-notification Independence

`--test-notification` now runs before `load_watchlists()` and does not require `watchlist.json` to be valid or even present. It attempts to read the first watchlist name for the notification title and falls back to `"TEST"` silently on any error.

### Input Validation

`--add` and `--clone` now loop until valid input is provided. Name and URL fields reject blank input with a prompt to re-enter. The seat list requires at least one entry before accepting.

### Unique Watchlist Names

All name-modifying commands (`--add`, `--clone`, `--edit`) enforce case-insensitive name uniqueness across all watchlists. Attempting to save a duplicate name prompts for a different name instead of proceeding. `--edit` correctly excludes the entry being edited from the duplicate check.

---

## v1.0 — 2026-06-07

Initial release.

---

### Core Tracking

#### watch_seats
Monitor specific named seats for a showtime. The tracker fetches the live AMC seat map, determines availability, and notifies on any status change in either direction (UNAVAILABLE → AVAILABLE or AVAILABLE → UNAVAILABLE). One Pushover notification is sent per seat per change.

```json
"watch_seats": ["J15", "J16", "J17"]
```

#### watch_any
Monitor a pool of seats and notify when any seat in the pool becomes newly AVAILABLE. Unlike `watch_seats`, this only fires on the UNAVAILABLE → AVAILABLE transition. All seats that become available in a single run are batched into one grouped Pushover notification.

```json
"watch_any": ["J13", "J14", "J15", "J16", "J17", "J18", "J19"]
```

A watchlist may use `watch_seats`, `watch_any`, or both simultaneously.

#### State Tracking
Seat status is persisted to `state.json` after every run, nested under the watchlist name. This enables change detection across runs and prevents repeated notifications for seats that remain in the same state.

```json
{
  "Thunderbolts Saturday": {
    "J15": "UNAVAILABLE",
    "J16": "UNAVAILABLE"
  }
}
```

Possible values: `AVAILABLE`, `UNAVAILABLE`, `NOT FOUND`.

---

### Watchlist Management

All management commands read from and write to `watchlist.json`. A timestamped backup is created automatically before every write.

#### --add
Interactively create a new watchlist entry. Prompts for name, showtime URL (validated non-blank), and seats (comma-separated, whitespace trimmed). Appends to the existing watchlists array.

```
py tracker_multiwatch.py --add
```

#### --edit INDEX
Interactively edit an existing watchlist entry selected by index (from `--show-watchlists`). Displays the current value of each field as the prompt default. Press Enter to keep, type a new value to replace, or type `-` to remove a list field (`watch_seats` or `watch_any`). Validates that the result still has at least one of `watch_seats` or `watch_any` before saving.

```
py tracker_multiwatch.py --edit 1
```

#### --clone INDEX
Duplicate an existing watchlist. Displays the source entry, then prompts for a new name (required, loops until non-blank) and an optional new showtime URL (Enter keeps the original). Warns if the entered URL is already used by another watchlist. The clone is always created with `enabled: true` regardless of the source state. Uses `deepcopy` so all fields are fully independent.

```
py tracker_multiwatch.py --clone 1
```

#### --show-watchlists
Print all configured watchlists with their index number, name, enabled status, showtime URL, `watch_seats`, and `watch_any`. No network access. No file modifications. Index numbers correspond to the `--edit`, `--clone`, `--enable`, `--disable`, and `--remove` commands.

```
py tracker_multiwatch.py --show-watchlists
```

#### --enable INDEX / --disable INDEX
Set the `enabled` field on a watchlist entry to `true` or `false` by index. Disabled watchlists are skipped entirely during a normal run — no page fetch, no seat check, no notification. Missing `enabled` field defaults to `true`.

```
py tracker_multiwatch.py --enable 1
py tracker_multiwatch.py --disable 2
```

#### --remove INDEX
Remove a watchlist entry by index. Requires confirmation (`yes/no`) before writing. All other watchlists are preserved. A backup is created before the write.

```
py tracker_multiwatch.py --remove 2
```

---

### Operations

#### --health
Verify the tracker environment without contacting AMC or modifying any files. Checks: `watchlist.json` exists and is valid JSON, `state.json` exists and is valid JSON (warning only if missing), `tracker.log` is writable, Playwright is installed, `requests` is installed, Pushover env vars are configured. Prints enabled and disabled watchlist counts. Reports `HEALTHY`, `HEALTHY (N warning(s))`, or `UNHEALTHY (N issue(s))`.

```
py tracker_multiwatch.py --health
```

#### --stats
Display a summary of the current configuration and file sizes without network access or file modifications. Shows total, enabled, and disabled watchlist counts; unique URLs; total `watch_seats` and `watch_any` entries; and sizes of `watchlist.json`, `state.json`, and `tracker.log`.

```
py tracker_multiwatch.py --stats
```

#### Run Summaries
At the end of every normal tracking run, a summary is printed to the console and logged to `tracker.log`:

```
## Run Summary
Watchlists processed : 2
  Enabled            : 2
  Disabled skipped   : 0
  Failed             : 0
Unique URLs          : 1
Cache hits           : 1
Cache misses         : 1
Notifications sent   : 0
Duration             : 11.42 sec
```

Notification count reflects actual Pushover posts attempted, not change detections. Duration is measured with a monotonic timer.

#### Log Rotation
`tracker.log` is automatically rotated at startup if it exceeds 5 MB, before the logger is initialized. Up to three archives are kept alongside the active log:

```
tracker.log      ← current run
tracker.log.1    ← previous
tracker.log.2    ← two runs ago
tracker.log.3    ← three runs ago
```

When rotation triggers, each file shifts up one position and `tracker.log.3` is deleted if present. A message is printed to the console listing each rename performed.

#### URL Caching
Each unique showtime URL is fetched at most once per run, regardless of how many watchlists reference it. The HTML is stored in an in-memory dict (`html_cache`) keyed by URL. Subsequent watchlists sharing the same URL reuse the cached HTML. Cache hits and misses are logged and included in the run summary. This eliminates redundant Playwright browser launches when tracking multiple showtimes at the same venue or URL.

---

### Notifications

#### Pushover Integration
AMCTracker sends push notifications via the [Pushover](https://pushover.net) API. Notifications require two environment variables:

| Variable | Description |
|---|---|
| `PUSHOVER_USER_KEY` | Your Pushover user key |
| `PUSHOVER_API_TOKEN` | Your Pushover application API token |

If either variable is missing, notifications are silently skipped — the tracker continues running normally.

**watch_seats notification:**
- Title: `AMC Seat Alert — {watchlist name}`
- Message: `{seat}: {old status} -> {new status}\n{showtime URL}`
- Fires once per seat per status change

**watch_any notification:**
- Title: `AMC Seat Alert — {watchlist name}`
- Message: `Available seats:\n{seat}\n{seat}\n{showtime URL}`
- Fires once per run when one or more newly-available seats are detected
- All newly-available seats are included in a single message

**Test notification:**
```
py tracker_multiwatch.py --test-notification
```
Sends a test message using the first watchlist's name. Does not fetch any AMC pages or modify state.

---

### Additional Utilities

#### --generate-block
Generate a contiguous seat block from a row letter, center seat number, and radius. Outputs both a plain list and a JSON-ready array for pasting into `watchlist.json`. No file modifications.

```
py tracker_multiwatch.py --generate-block
Row (e.g. J): J
Center seat number (e.g. 16): 16
Radius (e.g. 3): 3

J13
J14
J15
J16
J17
J18
J19

[
  "J13",
  "J14",
  "J15",
  "J16",
  "J17",
  "J18",
  "J19"
]
```

#### --list-seats "Name"
Fetch the live seat map for a named watchlist and display all currently AVAILABLE CanReserve seats, grouped by row and sorted left-to-right numerically. Useful for scouting available seats before configuring `watch_any`.

```
py tracker_multiwatch.py --list-seats "Thunderbolts Saturday"
```

#### --debug
Save the raw fetched HTML to `amc_seats_{slug}.html` for each watchlist processed. Useful for diagnosing seat extraction issues without modifying parsing logic.

#### --simulate-available SEAT
Override a specific seat to AVAILABLE for a single run. Triggers change detection and notifications as if the seat genuinely became available. Used for testing the notification pipeline end-to-end.
