# AMCTracker — CLAUDE.md

## Project Purpose

AMCTracker monitors AMC Theatre seat availability for specific showtimes. It fetches live seat maps via Playwright (headless Chromium), extracts seat status from the Next.js RSC payload embedded in the page HTML, compares against previously saved state, and sends Pushover push notifications when watched seats change status.

**Current version:** AMCTracker v1.0.5

---

## Architecture Overview

- **Single script:** `tracker_multiwatch.py` handles all logic — CLI parsing, page fetching, seat extraction, state diffing, notifications, and utility commands.
- **No server, no scheduler.** Intended to be run on a cron schedule or manually.
- **Data files** (`watchlist.json`, `state.json`) live alongside the script.
- **In-memory URL cache** prevents redundant page fetches when multiple watchlists share the same showtime URL.

---

## File Inventory

| File | Purpose |
|------|---------|
| `tracker_multiwatch.py` | Main tracker — all features live here |
| `tracker.py` | Original single-watchlist tracker (retained as reference, not used) |
| `watchlist.json` | Watchlists config — array of showtimes and seats to watch |
| `state.json` | Persisted seat status from last run, nested under watchlist name |
| `tracker.log` | Append-only run log (rotated at 5 MB) |
| `tracker.log.1/.2/.3` | Rotated log archives (up to 3 kept) |
| `PROJECT_STATUS.md` | Human-readable record of completed features and current state |
| `CLAUDE.md` | This file — context and rules for AI-assisted development |
| `extract_seats.py` | Dev tool — extracts seating layout from saved HTML |
| `check_seats.py` | Dev tool — Playwright fetcher, saves HTML to disk |
| `seat_counter.py` | Dev tool — counts available seats from a live URL |
| `amc_seats.html` | Last saved HTML snapshot (from `check_seats.py` or `--debug`) |
| `requirements.txt` | Python dependencies |
| `*.bak` / `*.bak.*` | Timestamped backups taken before each edit |

---

## watchlist.json Structure

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

| Field | Required | Default | Description |
|---|---|---|---|
| `name` | Yes | — | Human-readable label; used as key in `state.json` and Pushover title |
| `showtime_url` | Yes | — | Full AMC showtime seats URL |
| `enabled` | No | `true` | If `false`, watchlist is skipped entirely |
| `watch_seats` | Conditional | — | Specific seats to track; notifies on any status change |
| `watch_any` | Conditional | — | Seat pool; notifies when any seat becomes newly AVAILABLE |
| `watch_adjacent` | Conditional | — | Adjacent seat windows; notifies when `count` consecutive seats are all AVAILABLE |

At least one of `watch_seats`, `watch_any`, or `watch_adjacent` is required per entry.

---

## state.json Structure

Nested under watchlist name. Seat keys from `watch_seats`, `watch_any`, and `watch_adjacent` are all stored together under the same watchlist entry.

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

Values: `"AVAILABLE"`, `"UNAVAILABLE"`, `"NOT FOUND"`

`watch_adjacent` windows are stored under keys of the form `"adj:{seat1}-{seat2}"` (e.g. `"adj:K14-K15"`). These keys coexist with individual seat keys and serve the same purpose: change detection across runs, preventing re-notification for windows that remain available.

---

## Current Features

### CLI Flags

| Flag | Effect |
|------|--------|
| `--health` | Environment check — files, imports, Pushover config, watchlist counts |
| `--stats` | Watchlist counts, seat totals, file sizes |
| `--show-watchlists` | List all watchlists with index, enabled status, URL, watch_seats, watch_any, and watch_adjacent config |
| `--add` | Interactively add a new watchlist entry; select monitor mode (watch_seats, watch_any, or watch_adjacent) |
| `--edit INDEX` | Interactively edit a watchlist entry by index; includes `watch_adjacent` row and count editing |
| `--clone INDEX` | Clone a watchlist — prompts for new name and optional URL; pre-clone and post-clone summaries display all monitoring modes |
| `--enable INDEX` | Set `enabled: true` by index |
| `--disable INDEX` | Set `enabled: false` by index |
| `--remove INDEX` | Remove a watchlist by index (requires confirmation) |
| `--list-seats "Name"` | Fetch live seat map; display all available reservable seats by row |
| `--inspect INDEX` | Fetch a live seat map for a watchlist by index; display available reservable seats, adjacent windows available across all rows, and windows matching the watchlist criteria; read-only (no state changes, no notifications) |
| `--diagnose-seat-types INDEX` | Inspect raw seat object types and availability values; shows first 20 seat objects, grouped type/availability counts, and reservable seat total (diagnostic only) |
| `--generate-block` | Generate seat list from row + center + radius; outputs plain and JSON |
| `--debug` | Save raw HTML to `amc_seats_{slug}.html` per watchlist |
| `--simulate-available SEAT` | Override a seat to AVAILABLE for one run (testing) |
| `--test-notification` | Send a test Pushover message using the first watchlist and exit |
| `--json-output PATH` | Write a versioned JSON run summary to PATH after each tracking run (optional; never affects console output or notifications) |

### watch_seats behavior
- Tracks specific named seats
- Notifies on **any** status change (UNAVAILABLE→AVAILABLE or vice versa)
- One Pushover notification per seat per change
- Pushover title: `AMC Seat Alert — {watchlist name}`
- Message: `{seat}: {old} -> {new}\n{url}`

### watch_any behavior
- Monitors a pool of seats
- Notifies only when a seat transitions to AVAILABLE (not when it goes unavailable)
- All newly-available seats batched into **one** Pushover notification per run
- Pushover title: `AMC Seat Alert — {watchlist name}`
- Message: `Available seats:\n{seat}\n{seat}\n{url}`
- State tracking prevents re-notifying for the same available seat across runs

### watch_adjacent behavior
- Configured as an array of `{rows, count}` objects per watchlist entry
- For each entry, discovers all seats in the specified rows from the live seat map
- Generates every consecutive window of `count` seats within each row
- Notifies when all seats in a window transition from not-fully-available to fully-available
- Only fires on the UNAVAILABLE -> AVAILABLE transition for the window as a whole
- All newly-available windows for one entry are batched into **one** Pushover notification per run
- Pushover title: `AMC Seat Alert — {watchlist name}`
- Message: `Adjacent seats available:\n\n{window}\n{window}\n{url}`
- State stored under `adj:{seat1}-{seat2}` keys — prevents re-notification across runs
- `count` defaults to `2`; any value >= 2 is supported without schema changes
- Rows with no seats in the live seat map are silently skipped

### Seat range expansion
- Applies to `watch_seats` and `watch_any` inputs in `--add` and `--edit`
- Ranges use the form `ROW#-ROW#` (e.g. `J1-J29`, `K10-K15`)
- Commas mix ranges and individual seats (e.g. `J1-J5,K10`)
- Ranges are expanded to individual seat names before saving to `watchlist.json`
- Validation rules:
  - Both sides of a range must share the same row letter (`J5-K10` is rejected)
  - Start number must be <= end number (`J10-J5` is rejected)
  - Tokens must match `ROW#` or `ROW#-ROW#` exactly (`J1-5` is rejected)
- On error, the prompt re-displays for correction (no partial saves)

### watch_adjacent row input
- Applies to `watch_adjacent` `rows` and `count` fields in `--add` and `--edit`
- Accepted row formats:
  - Range: `H-K` (expands to `H`, `I`, `J`, `K`)
  - Comma-separated: `H,I,J,K`
  - Single letter: `J`
  - Mixed: `H-K,M` (expands to `H`, `I`, `J`, `K`, `M`)
- Ranges expand to individual row letters before saving; `watchlist.json` stores the explicit list
- Validation rules:
  - Each token must be a single letter A-Z or a two-letter range (`X-Y`)
  - Descending ranges (`K-H`) are rejected
  - Multi-character tokens (`AB`) are rejected
  - On error, the prompt re-displays for correction (no partial saves)
- `count` accepts any integer >= 2; invalid input re-prompts
- In `--add`: rows are required (blank re-prompts); count defaults to `2` (press Enter to accept)
- In `--edit`: press Enter at either prompt to keep the current value; if `watch_adjacent` is absent, prompts are skipped; multiple entries prompted in sequence, labeled `1 of N` / `2 of N`

---

## Notification Flow

1. Pushover credentials read from env vars: `PUSHOVER_USER_KEY`, `PUSHOVER_API_TOKEN`
2. If either is missing, `send_notification()` / `send_any_notification()` / `send_adjacent_notification()` return `False` silently
3. `requests.post()` to `https://api.pushover.net/1/messages.json`
4. `RequestException` is caught and swallowed — network failures do not crash the tracker
5. All three functions return `bool`: `True` if post was attempted, `False` if env vars missing
6. Return value is used by the run summary to count actual notification sends

---

## Logging Flow

- Log file: `tracker.log` (append-only)
- Format: `YYYY-MM-DD HH:MM:SS  message`
- Initialized via `logging.basicConfig()` after log rotation check
- **Log rotation** runs automatically at startup before `logging.basicConfig()`:
  - Threshold: 5 MB
  - Chain: `.3` deleted → `.2→.3` → `.1→.2` → `tracker.log→tracker.log.1`
  - Maximum files retained: `tracker.log` + `.1` + `.2` + `.3`
- Key log events: run start, per-seat status, cache hits/misses, changes, notifications sent, run summary

### Run Summary (logged every normal run)
```
RUN SUMMARY | processed=1 skipped=0 failed=0 challenge=0 expired=0 parse=0 playwright=0 unique_urls=1 cache_hits=0 cache_misses=1 notifications=0 duration=11.31s
```

The log line always includes all four failure sub-counts (zero when clean). Console output adds a breakdown block only when `failed > 0`:
```
  Failed             : 2
    Challenge/bot    : 1
    Expired URL      : 1
    Parse error      : 0
    Playwright error : 0
```

---

## Failure Classification

When a watchlist raises an exception during a normal run, `classify_page_failure(html, exc)` determines the category using two durable signals — HTML size and seatingLayout keyword presence — before examining the exception type. No vendor-specific strings are used.

| Label | Console prefix | Condition | Log level | Meaning |
|---|---|---|---|---|
| `CHALLENGE_PAGE` | `[CHALLENGE_PAGE]` | ValueError + `len(html) < 200,000` | WARNING | Cloudflare or bot-protection block; transient, retry next run |
| `EXPIRED_URL` | `[EXPIRED_URL]` | ValueError + large page + no seatingLayout | WARNING | Full AMC page loaded but no seat data; showtime may be expired |
| `PARSE_ERROR` | `[PARSE_ERROR]` | ValueError + large page + seatingLayout present | EXCEPTION (with traceback) | JSON extraction failed; likely AMC page structure change |
| `PLAYWRIGHT_ERROR` | `[PLAYWRIGHT_ERROR]` | Non-ValueError exception | EXCEPTION (with traceback) | Browser launch, navigation, or timeout failure |

`_SMALL_PAGE_THRESHOLD = 200_000` chars (~200KB). Confirmed Cloudflare Error 1015 block pages are ~7KB; confirmed minimum real AMC seat page is ~944KB — a 129x margin.

`CHALLENGE_PAGE` and `EXPIRED_URL` log at WARNING (no stack trace) — expected failure modes requiring no code investigation. `PARSE_ERROR` and `PLAYWRIGHT_ERROR` log at EXCEPTION (with stack trace) — require developer attention.

`html = ""` is initialized before each per-watchlist `try:` block so the except branch can always call `classify_page_failure(html, exc)` safely even if `fetch_html()` raised before returning.

---

## URL Caching Behavior

- `html_cache = {}` initialized once per run in `main()`
- Key: showtime URL string; Value: fetched HTML
- Before every `fetch_html()` call:
  - **Cache miss** → fetch, store, log `CACHE MISS`, increment `cache_misses`
  - **Cache hit** → reuse, print `(cache hit -- reusing fetched HTML)`, log `CACHE HIT`, increment `cache_hits`
- Eliminated redundant page loads when multiple watchlists share the same URL

---

## Health Check Behavior (`--health`)

Runs all checks without network access or file modifications:

| Check | Pass | Warn | Fail |
|---|---|---|---|
| `watchlist.json` exists | `[OK]` | — | `[FAIL]` |
| `watchlist.json` valid JSON | `[OK]` | — | `[FAIL]` |
| `state.json` exists | `[OK]` | `[WARN]` (first run?) | — |
| `state.json` valid JSON | `[OK]` | — | `[FAIL]` |
| `tracker.log` writable | `[OK]` | — | `[FAIL]` |
| Playwright installed | `[OK]` | — | `[FAIL]` |
| requests installed | `[OK]` | — | `[FAIL]` |
| Pushover env vars set | `[OK]` | `[WARN]` | — |

- `HEALTHY` = no failures
- `HEALTHY (N warning(s))` = warnings only
- `UNHEALTHY (N issue(s))` = one or more failures

---

## JSON Output Schema (`--json-output`) — schema_version 1 (frozen)

When `--json-output PATH` is passed, the tracker writes a run summary JSON file after saving state. Failures during the write are logged at WARNING and never crash the tracker. Console output and notifications are unchanged.

All timestamps are UTC with timezone offset (`+00:00`). The internal `failure_type` constants (`CHALLENGE_PAGE`, etc.) are normalized to `lower_snake_case` at the JSON boundary; console and log output retain the uppercase form.

### Top-level structure

```json
{
  "schema_version": 1,
  "generated_by": "AMCTracker",
  "generated_at": "2026-06-29T18:32:01.114853+00:00",
  "run_id": "<UUID v4>",
  "started_at": "2026-06-29T18:31:50.223401+00:00",
  "completed_at": "2026-06-29T18:32:01.988762+00:00",
  "duration_seconds": 11.765,
  "tracker_version": "1.0.5",
  "hostname": "<machine hostname>",
  "run_status": "success",
  "summary": { ... },
  "failure_breakdown": { ... },
  "watchlists": [ ... ]
}
```

**`generated_at`** — timestamp when the JSON document was assembled (milliseconds after `completed_at`). Retained for multi-service deployment tracing.

**`run_status`** values: `"success"` (0 failed), `"partial_failure"` (>0 failed and >0 succeeded), `"failed"` (all enabled watchlists failed).

### `summary` object

```json
{
  "total_watchlists": 3,
  "succeeded": 2,
  "disabled": 1,
  "failed": 0,
  "notifications_sent": 1,
  "cache_hits": 1,
  "cache_misses": 1
}
```

**`total_watchlists`** = `succeeded + disabled + failed` (every watchlist entry evaluated).

**`succeeded`** = watchlists that ran and completed without exception (enabled in config AND no error).

### `failure_breakdown` object

```json
{
  "challenge_pages": 0,
  "expired_urls": 0,
  "parse_errors": 0,
  "playwright_errors": 0
}
```

Always present; all zeros on a clean run.

### Per-watchlist object (in `watchlists` array)

```json
{
  "name": "The Odyssey - Wed Jul 22",
  "enabled": true,
  "showtime_url": "https://...",
  "monitoring": {
    "watch_seats": ["J15", "J16"],
    "watch_any": ["J13", "J14"],
    "watch_adjacent": [{"rows": ["I", "J", "K"], "count": 2}]
  },
  "status": "success",
  "seats_available": 3,
  "adjacent_windows_available": 2,
  "notification_sent": false,
  "failure_type": null,
  "error_message": null
}
```

**`monitoring` keys** (`watch_seats`, `watch_any`, `watch_adjacent`) are only present if configured. Empty arrays are omitted.

**`status`** values: `"success"`, `"skipped"` (disabled in config), `"failed"` (exception raised).

**`failure_type`** values (when `status="failed"`): `"challenge_page"`, `"expired_url"`, `"parse_error"`, `"playwright_error"`.

**`seats_available`** — count of non-`adj:` keys in `current` with value `"AVAILABLE"`.

**`adjacent_windows_available`** — count of `adj:`-prefixed keys with value `"AVAILABLE"`.

---

## Development Rules

### Windows / Claude Code Workflow

1. **Never generate long `python -c` one-liners.** Windows command-line parsing fails silently on complex quoting.
2. **Never generate long inline PowerShell commands** with nested quoting, multiple operations, or embedded Python.
3. **For any Python task longer than a few lines:** write a temporary `.py` file using the Write tool, execute with `py filename.py`, delete with `Remove-Item` afterward.
4. **Keep PowerShell commands short and simple.** Prefer the Edit/Write tools for file modifications over shell commands that rewrite files.

### Backups

5. **Prefer `git commit` before modifying `tracker_multiwatch.py`.** If Git is unavailable, use a short `Copy-Item` command (`Copy-Item tracker_multiwatch.py tracker_multiwatch.py.bak`). Only use timestamped `.bak.YYYYMMDD_HHMMSS` filenames when explicitly requested.
6. **All watchlist-modifying commands** (`--add`, `--edit`, `--clone`, `--enable`, `--disable`, `--remove`) must create a timestamped backup of `watchlist.json` before writing. This is automatic in-code behavior, not a manual step.

### Planning

7. **Before any non-trivial code change:** identify the exact files and line ranges to be modified, describe the plan, wait for explicit approval before editing.
8. **Compile-check after every code change:** `py -m py_compile tracker_multiwatch.py`. Do not proceed if this fails.

### Implementation Style

9. **Prefer incremental changes.** One feature at a time. Do not refactor surrounding code unless the task requires it.
10. **Preserve backward compatibility.** Existing `watchlist.json` files and `state.json` files must continue to work.
11. **No Unicode characters in print output.** The Windows terminal (cp1252) rejects characters outside ASCII/cp1252. Use `[OK]`, `[WARN]`, `[FAIL]`, `->` instead of `✓`, `→`, etc.
12. **Utility commands** (`--health`, `--stats`, `--show-watchlists`, `--generate-block`) must not fetch AMC pages or modify files.
13. **Notification behavior is stable.** Do not change notification logic, Pushover payload format, or env var names without explicit instruction.
14. **Do not modify AMC parsing logic** (`extract_seating_layout`, `collect_seats`) without first validating against a saved HTML snapshot (`amc_seats.html`).

### Public API / JSON Design

15. **All exported JSON is a versioned API contract.** Always include `schema_version` (integer) and `tracker_version` (semver string) at the top level of any exported JSON document.
16. **Build JSON dicts explicitly.** Never use `dataclasses.asdict()` or `vars()` to generate the public JSON output. Construct dicts field-by-field so the schema is visible and intentional.
17. **Only include keys that are present in config.** Omit optional monitoring keys (`watch_seats`, `watch_any`, `watch_adjacent`) from the exported dict when the watchlist does not configure them.
18. **JSON write failures must never crash the tracker.** Wrap all JSON file writes in `try/except` and log at `WARNING` level on failure.

### Documentation

19. **When adding a CLI flag or feature:** update `CLAUDE.md` (CLI flags table), `PROJECT_STATUS.md` (features table), and `RELEASE_NOTES.md` (new version section).
20. **When bumping the version:** update `TRACKER_VERSION` constant in `tracker_multiwatch.py` and the version references in `CLAUDE.md` and `PROJECT_STATUS.md`.

---

## AMC Seat Extraction Notes

- The seat map is embedded in the Next.js RSC payload as `seatingLayout` JSON
- Extracted via brace-balanced string walking (not an HTML parser)
- A valid seat object contains keys: `available`, `type`, `name`
- A seat is counted as reservable if: `available is True` AND `type in RESERVABLE_TYPES`
- `seatTier` is informational only (e.g. `"Regular"`)

### RESERVABLE_TYPES

Current reservable seat types:

- `CanReserve`
- `LoveSeatLeft`
- `LoveSeatRight`

These are the reservable seat types currently recognized by the tracker. Additional AMC auditorium-specific seat types may exist and may be added to `RESERVABLE_TYPES` in future versions after validation. Any type not present in `RESERVABLE_TYPES` is treated as non-reservable by default.

AMC auditoriums use different seat type names depending on configuration:

| Type | Description |
|---|---|
| `CanReserve` | Standard reservable seat (non-loveseat auditoriums) |
| `LoveSeatLeft` | Left half of a paired loveseat (premium/recliner auditoriums) |
| `LoveSeatRight` | Right half of a paired loveseat (premium/recliner auditoriums) |
| `Wheelchair` | Wheelchair accessible space — excluded from all reservable counts |
| `Companion` | Companion seat next to a wheelchair space — excluded from all reservable counts |

### Allowlist Behavior

The tracker intentionally uses an allowlist rather than a blocklist. Unknown seat types are excluded until explicitly validated and added to `RESERVABLE_TYPES`. This prevents accessibility seats or future AMC seat types from being incorrectly treated as reservable inventory.

### Page Load Strategy

`fetch_html()` uses a condition-based wait after navigation:

1. `page.wait_for_load_state("networkidle", timeout=15_000)` — waits until no network connections have been active for 500ms, which is the reliable signal that AMC's RSC stream has finished delivering seat data
2. If `networkidle` raises `PlaywrightTimeoutError` (e.g. analytics traffic prevents idle) — falls back to `page.wait_for_timeout(12_000)`

The previous implementation used a fixed `page.wait_for_timeout(8_000)` which could capture partial seat maps before AMC's RSC payload had fully streamed.

### LoveSeat Auditoriums

Some AMC auditoriums use paired loveseat configurations where every seat is typed `LoveSeatLeft` or `LoveSeatRight` instead of `CanReserve`. Both types are included in `RESERVABLE_TYPES` and participate in all availability checks: seat status tracking, `watch_any`, `watch_adjacent` window detection, `--inspect`, and `--list-seats`. A tracker using only `type == "CanReserve"` would silently report zero available seats in a loveseat auditorium even when dozens are shown in the AMC UI.

Use `--diagnose-seat-types INDEX` to inspect which seat types are present in any auditorium before configuring a watchlist.
