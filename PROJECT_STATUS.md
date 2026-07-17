# AMCTracker — Project Status

## Current State (2026-06-29)

### Working
- `tracker_multiwatch.py` loads a `watchlists` array from `watchlist.json` and processes each enabled entry sequentially
- Playwright fetches the live AMC seat page (headless Chromium)
- `seatingLayout` JSON is extracted from the Next.js RSC payload via brace-balancing
- Per-seat status (AVAILABLE / UNAVAILABLE) is determined and printed
- `state.json` persists seat status across runs, nested under watchlist name
- Change detection compares current vs previous state and prints CHANGE DETECTED
- Pushover notifications fire on change (requires `PUSHOVER_USER_KEY` and `PUSHOVER_API_TOKEN` env vars)
- `tracker.log` records every run, seat status, changes, and notification sends

### Flags
| Flag | Effect |
|------|--------|
| `--show-watchlists` | Print all configured watchlists (index, name, enabled, URL, watch_seats, watch_any, watch_adjacent) |
| `--add` | Interactively add a new watchlist entry to `watchlist.json` |
| `--edit INDEX` | Interactively edit a watchlist entry by index |
| `--enable INDEX` | Enable watchlist by index |
| `--disable INDEX` | Disable watchlist by index |
| `--remove INDEX` | Remove watchlist by index (requires confirmation) |
| `--clone INDEX` | Clone watchlist by index — prompts for new name and optional URL |
| `--stats` | Show watchlist counts, seat entry totals, and file sizes |
| `--list-seats "Name"` | Fetch live seat map and display all available reservable seats grouped by row |
| `--inspect INDEX` | Fetch a live seat map for a watchlist by index; display available reservable seats, adjacent windows available across all rows, and windows matching the watchlist criteria; read-only (no state changes, no notifications) |
| `--diagnose-seat-types INDEX` | Inspect raw seat object types and availability values; shows first 20 seat objects, type/availability grouped counts, and reservable seat totals (diagnostic only) |
| `--generate-block` | Generate a seat block from row, center seat, and radius; outputs plain list and JSON |
| `--health` | Verify tracker environment without contacting AMC |
| `--debug` | Saves raw HTML to `amc_seats_{slug}.html` per watchlist |
| `--simulate-available SEAT` | Marks seat AVAILABLE for one run |
| `--test-notification` | Sends test Pushover message using first watchlist name and exits |
| `--json-output PATH` | Writes a versioned JSON run summary to PATH after each tracking run |

---

## Completed Features

### --json-output — v1.0.5 (2026-06-29)  [schema_version 1 frozen]
- New optional `--json-output PATH` CLI flag writes a versioned JSON run summary after each tracking run
- JSON file is a stable, versioned API contract (`schema_version: 1`) — the interface between the tracker engine and future services
- Never crashes the tracker — write failures are caught and logged at WARNING
- Console output, notifications, state.json, and all existing behavior are unchanged
- All timestamps are UTC with timezone offset (`+00:00`)
- Top-level fields: `schema_version`, `generated_by`, `generated_at`, `run_id` (UUID v4), `started_at`, `completed_at`, `duration_seconds`, `tracker_version`, `hostname`, `run_status`
- `run_status`: `"success"` (0 failed), `"partial_failure"` (some failed), `"failed"` (all enabled failed)
- `summary` object: `total_watchlists`, `succeeded`, `disabled`, `failed`, `notifications_sent`, `cache_hits`, `cache_misses`
- `failure_breakdown` object: `challenge_pages`, `expired_urls`, `parse_errors`, `playwright_errors`
- `watchlists` array: one object per watchlist with `name`, `enabled`, `showtime_url`, `monitoring`, `status`, `seats_available`, `adjacent_windows_available`, `notification_sent`, `failure_type`, `error_message`
- `failure_type` values: `"challenge_page"`, `"expired_url"`, `"parse_error"`, `"playwright_error"` (normalized to lowercase at JSON boundary; console retains uppercase)
- JSON is built explicitly field-by-field — never via `dataclasses.asdict()`

### Failure Classification — v1.0.4 (2026-06-12)
- `classify_page_failure(html, exc)` helper classifies per-watchlist errors into four labeled categories
- `_SMALL_PAGE_THRESHOLD = 200_000` chars distinguishes bot-protection pages (~7KB) from real AMC seat pages (~944KB+)
- `CHALLENGE_PAGE` — Cloudflare or rate-limit block; logged at WARNING (no stack trace)
- `EXPIRED_URL` — full page loaded but no seatingLayout; showtime may be expired; logged at WARNING
- `PARSE_ERROR` — seatingLayout found but unparseable; logged at EXCEPTION with traceback
- `PLAYWRIGHT_ERROR` — browser/navigation/timeout failure; logged at EXCEPTION with traceback
- `html = ""` sentinel before each per-watchlist `try:` block ensures the except branch can always call the classifier
- Run summary shows failure sub-breakdown (`Challenge/bot`, `Expired URL`, `Parse error`, `Playwright error`) only when `failed > 0`; clean runs are unchanged
- Log line always includes all four sub-counts: `challenge=N expired=N parse=N playwright=N`
- No changes to success path, notification behavior, state.json handling, or watchlist.json handling

### Multi-Watchlist Refactor (2026-06-07)
- `tracker_multiwatch.py` is the main tracker (replaces `tracker.py`)
- `watchlist.json` uses a `watchlists` array (one entry per showtime)
- `state.json` nested under watchlist name
- Pushover title includes watchlist name

### --add (2026-06-07)
- Prompts for name, URL, then monitor mode (watch_seats / watch_any / watch_adjacent); default is watch_seats (Enter)
- **watch_seats / watch_any:** prompts for seats (comma-separated, ranges ok e.g. `J1-J5`); saves under the selected key
- **watch_adjacent:** prompts for rows (range `G-L`, comma-separated `G,H,I`, or single letter `J`) and count (integer >= 2, default 2); row ranges expand to individual letters before saving
- Validates URL is not blank
- Creates timestamped backup of `watchlist.json` before writing
- Appends new entry, preserves existing watchlists

### --list-seats (2026-06-07)
- Accepts watchlist name as argument
- Fetches live seat map for that watchlist's URL
- Displays all AVAILABLE CanReserve seats grouped by row, sorted left-to-right
- Error if watchlist name not found; lists available names

### watch_any (2026-06-07)
- Optional `watch_any` list in each watchlist entry (alongside or instead of `watch_seats`)
- Notifies when any seat in the pool becomes newly AVAILABLE (grouped into one notification)
- Notification title: `AMC Seat Alert — {watchlist name}`
- Notification body: `Available seats:\n{seat}\n{seat}\n{url}`
- State tracking prevents repeated notifications for the same seat
- `watch_seats` behavior and notifications unchanged
- A watchlist may have `watch_seats`, `watch_any`, or both

### Run Summary Logging (2026-06-07)
- Printed to console and logged to `tracker.log` at the end of every normal tracking run
- Tracks: watchlists processed, enabled, disabled skipped, failed, unique URLs, cache hits, cache misses, notifications sent, runtime duration
- `send_notification()` and `send_any_notification()` return `bool` — `True` if post was attempted
- Timer uses `time.monotonic()` for accurate wall-clock duration

### Log Rotation (2026-06-07)
- Runs automatically at startup before `logging.basicConfig()`
- Threshold: 5 MB (`LOG_MAX_BYTES = 5 * 1024 * 1024`)
- Rotation chain: `tracker.log.3` deleted → `.2 -> .3` → `.1 -> .2` → `tracker.log -> tracker.log.1`
- Keeps at most: `tracker.log`, `tracker.log.1`, `tracker.log.2`, `tracker.log.3`
- Prints each rename step to console when triggered; silent when below threshold

### URL fetch caching (2026-06-07)
- `html_cache = {}` initialized once per run in `main()`
- Before calling `fetch_html()`, checks cache by URL
- Cache miss: fetches page, stores result; logs `CACHE MISS`
- Cache hit: reuses stored HTML, prints `(cache hit)`; logs `CACHE HIT`
- Multiple watchlists sharing the same URL incur only one network fetch per run

### --stats (2026-06-07)
- Reads `watchlist.json` directly — no validation, no network access, no file writes
- Displays: total/enabled/disabled watchlists, unique URLs, total watch_seats and watch_any entries
- Displays file sizes for `watchlist.json`, `state.json`, `tracker.log`

### --generate-block (2026-06-07)
- Prompts for row letter, center seat number, and radius
- Outputs the resulting seat list plain, then JSON-ready format
- Utility only — no file modifications, no watchlist changes

### --show-watchlists (2026-06-07)
- Reads `watchlist.json` and prints every watchlist entry
- Displays: index, name, enabled status (defaults Yes if field missing), URL, watch_seats, watch_any
- No network access, no file writes

### enabled field (2026-06-07)
- Optional `"enabled": true|false` field per watchlist entry
- Missing field defaults to `true`
- Disabled watchlists are skipped in the main run loop — no page fetch, no seat check, no notification
- `--show-watchlists` displays enabled status as Yes/No

### --enable / --disable (2026-06-07)
- Accept 1-based index from `--show-watchlists`
- Create timestamped backup of `watchlist.json` before writing
- Set `enabled: true` or `enabled: false` on the target entry
- All other watchlists preserved

### --remove (2026-06-07)
- Accepts 1-based index from `--show-watchlists`
- Prompts for confirmation (`yes/no`) before removing
- Creates timestamped backup before writing
- All other watchlists preserved

### --clone (2026-06-07)
- Accepts 1-based index from `--show-watchlists`
- Displays source watchlist name and all monitoring modes (watch_seats, watch_any, watch_adjacent rows/count) before prompting
- Prompts for new name (required, loops until non-blank)
- Prompts for new URL (optional — Enter keeps original URL)
- Warns if entered URL is already used by another watchlist; asks to continue
- Sets `enabled: true` on clone regardless of source state
- Uses `deepcopy` so all current and future fields are fully independent
- Creates timestamped backup before writing
- Post-clone summary displays all monitoring modes present in the cloned watchlist
- All existing watchlists preserved

### --edit (2026-06-07)
- Accepts 1-based index from `--show-watchlists`
- Displays current value for each field as prompt default
- Press Enter to keep current value; type new value to replace
- `-` removes a list field (`watch_seats` or `watch_any`)
- Interactively edits `watch_adjacent` entries when present:
  - Prompts for rows (range `H-K`, comma-separated `H,I,J,K`, single letter `J`, or mixed)
  - Row ranges expand to individual letters before saving
  - Descending ranges and multi-character tokens rejected; prompt loops on error
  - Prompts for count (integer >= 2); prompt loops on invalid input
  - Press Enter at either prompt to keep the current value
  - Multiple entries prompted in sequence, labeled `1 of N` / `2 of N`
- Validates result still has `watch_seats`, `watch_any`, or `watch_adjacent` before saving
- `watch_adjacent`-only watchlists now pass the monitoring-mode validation check during editing
- Creates timestamped backup before writing
- All other watchlists preserved

### Reliability Sprint — v1.0.1 (2026-06-07)

#### Per-watchlist exception isolation
- Each watchlist in the main loop is wrapped in an independent `try/except` block
- Errors in one watchlist are caught, printed, and logged without stopping other watchlists
- `failed` counter incremented per error; included in run summary

#### Atomic state writes
- `save_state()` writes to `state.json.tmp` first, then renames to `state.json`
- Prevents partial/corrupt `state.json` if the process is killed mid-write
- `state.json.tmp` is transient; safe to delete if found

#### --test-notification independence
- Moved before `load_watchlists()` — runs without requiring `watchlist.json` to be valid
- Reads first watchlist name for notification title; falls back to `"TEST"` on any error

#### Input validation loops
- `--add` and `--clone` loop on blank name, URL, and seat list input
- Accepts input only after non-blank values are entered

### Unique Watchlist Names (2026-06-07)
- `--add`, `--clone`, and `--edit` enforce case-insensitive uniqueness across all watchlist names
- Duplicate name rejected with a prompt to enter a different name
- `--edit` excludes the current entry's own name from the duplicate check

### watch_adjacent (2026-06-07)
- Optional `watch_adjacent` array per watchlist entry
- Each entry specifies `rows` (list of row letters) and `count` (window size, default 2)
- Discovers seats in specified rows from the live seat map; generates all consecutive windows
- Notifies when a full window of `count` seats becomes newly AVAILABLE (batched per run)
- Notification title: `AMC Seat Alert — {watchlist name}`
- Notification body: `Adjacent seats available:\n\n{window}\n{url}`
- State tracked under `adj:{seat1}-{seat2}` keys; prevents re-notification across runs
- Rows with no seats in the live seat map are silently skipped
- `count` defaults to 2; any value >= 2 supported without schema changes
- A watchlist with only `watch_adjacent` (no `watch_seats` or `watch_any`) is valid

### --inspect (2026-06-07)
- Accepts 1-based index from `--show-watchlists`
- Fetches live seat map for the selected watchlist
- Displays total seats in the layout and total available CanReserve seats
- Shows all available adjacent windows across every row in the layout (using first `watch_adjacent` count, or 2 if not configured)
- Shows matching watchlist criteria: available windows per `watch_adjacent` config entry, `watch_seats` availability, `watch_any` availability
- Prints a summary: available seats discovered, total windows available (all rows), windows matching watchlist criteria
- Read-only — does not modify `state.json`, `watchlist.json`, or send notifications

### --show-watchlists watch_adjacent display (2026-06-07)
- `--show-watchlists` now displays `watch_adjacent` config for each watchlist
- Shows `Rows` and `Count` for each adjacent config entry
- Supports multiple `watch_adjacent` entries per watchlist

### Seat Range Expansion (2026-06-07)
- `--add` and `--edit` accept seat ranges in `ROW#-ROW#` form for `watch_seats` and `watch_any`
- Ranges are expanded to individual seats before saving; `watchlist.json` stores the full explicit list
- Mixed input supported: `J1-J5,K10` expands to `J1, J2, J3, J4, J5, K10`
- Rejected: cross-row ranges (`J5-K10`), descending ranges (`J10-J5`), malformed tokens (`J1-5`)
- Invalid input re-prompts; no partial saves

### Hydration Reliability Improvements (2026-06-10)
- Replaced fixed `page.wait_for_timeout(8_000)` with `page.wait_for_load_state("networkidle", timeout=15_000)` after navigation
- Falls back to `page.wait_for_timeout(12_000)` if `networkidle` raises `PlaywrightTimeoutError`
- Eliminates partial seat-map captures caused by AMC's RSC payload not fully streaming within 8 seconds
- Root cause confirmed via `--diagnose-layout`: partial snapshot showed 116 seats / 4 available; full snapshot showed 116 seats / 63 available after fix

### LoveSeat Theater Support (2026-06-10)
- Current reservable seat types: `CanReserve`, `LoveSeatLeft`, `LoveSeatRight`
- All production availability checks now use `type in RESERVABLE_TYPES` instead of `type == "CanReserve"`
- Additional AMC auditorium-specific seat types may be added to `RESERVABLE_TYPES` in future versions after validation
- `Wheelchair` and `Companion` seat types remain excluded from all availability counts
- Fixes false negatives in loveseat auditoriums where all seats are typed `LoveSeatLeft` / `LoveSeatRight`
- Applies to: seat status tracking, `watch_any`, `watch_adjacent` window detection, `--inspect`, `--list-seats`
- Validation: Scary Movie June 10 — available seats: 4 -> 63; matching watch_adjacent windows: 0 -> 9

### --diagnose-seat-types (2026-06-10)
- Accepts 1-based index from `--show-watchlists`
- Fetches live seat map using the production pipeline (fetch, extract, collect)
- Displays first 20 seat objects with `name`, `available`, and `type` fields
- Displays counts grouped by `(type, available)` for all seat objects in the layout
- Reports: `available is True` count, `available == True` count, `type == CanReserve` count, production filter count
- Diagnostic only — no state changes, no notifications, no file writes

---

## watchlist.json structure
```json
{
  "watchlists": [
    {
      "name": "The Odyssey - Wed Jul 22",
      "showtime_url": "https://www.amctheatres.com/showtimes/143822631/seats",
      "enabled": true,
      "watch_seats": ["J15", "J16", "J17"],
      "watch_any": ["J13", "J14", "J15", "J16", "J17", "J18", "J19"],
      "watch_adjacent": [
        {"rows": ["I", "J", "K", "L", "M"], "count": 2}
      ]
    }
  ]
}
```

## state.json structure
```json
{
  "The Odyssey - Wed Jul 22": {
    "J15": "UNAVAILABLE",
    "J16": "UNAVAILABLE",
    "J13": "UNAVAILABLE",
    "adj:J14-J15": "UNAVAILABLE",
    "adj:J15-J16": "UNAVAILABLE"
  }
}
```

---

## File Inventory

| File | Purpose |
|------|---------|
| `tracker_multiwatch.py` | Main tracker — multi-watchlist, fetch, extract, diff, notify |
| `tracker.py` | Original single-watchlist tracker (retained as reference) |
| `watchlist.json` | Watchlists config (multi-watchlist format) |
| `state.json` | Persisted seat status from last run (nested by watchlist name) |
| `state.json.tmp` | Transient atomic write buffer; deleted immediately after each save; safe to remove if found |
| `tracker.log` | Append-only run log (rotated at 5 MB) |
| `tracker.log.1/.2/.3` | Rotated log archives (up to 3 kept) |
| `extract_seats.py` | Dev tool — extracts and prints seating layout from saved HTML |
| `check_seats.py` | Dev tool — Playwright page fetcher, saves HTML |
| `seat_counter.py` | Dev tool — counts available seats from a live URL |
| `amc_seats.html` | Last saved HTML snapshot (from check_seats.py or --debug) |
| `requirements.txt` | Python dependencies |
| `*.bak` / `*.bak.*` | Timestamped backups taken before each edit |
