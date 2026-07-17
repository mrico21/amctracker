# AMCTracker — Recovery Guide

## Restore watchlist.json from Backup

Backups are created automatically before every write operation. They follow the naming pattern:

```
watchlist.json.bak.YYYYMMDD_HHMMSS
```

**To restore:**

1. List available backups:
   ```powershell
   Get-ChildItem C:\AMCTracker\watchlist.json.bak.* | Sort-Object LastWriteTime -Descending
   ```

2. Copy the desired backup over the current file:
   ```powershell
   Copy-Item "C:\AMCTracker\watchlist.json.bak.20260607_114120" "C:\AMCTracker\watchlist.json"
   ```

3. Verify the restored file is valid JSON:
   ```powershell
   py -c "import json; json.load(open('C:\AMCTracker\watchlist.json')); print('VALID')"
   ```

4. Confirm contents:
   ```powershell
   py C:\AMCTracker\tracker_multiwatch.py --show-watchlists
   ```

---

## Reset or Recover state.json

`state.json` holds the last-known seat status. The tracker does not create timestamped backups of this file — only `watchlist.json` gets backups.

If `state.json` is corrupted or missing, delete it:

```powershell
Remove-Item C:\AMCTracker\state.json
```

The tracker will create a fresh one on the next run. You may see extra change notifications on that first run, as it has no prior baseline to compare against.

> **state.json.tmp:** If you find a `state.json.tmp` file in the tracker directory, it is a leftover from a write that was interrupted before completing. It is safe to delete.

---

## Reinstall Playwright

Playwright requires both the Python package and the browser binary (Chromium).

**Step 1 — Reinstall the Python package:**
```powershell
pip install playwright
```

**Step 2 — Install the Chromium browser:**
```powershell
playwright install chromium
```

**Step 3 — Verify:**
```powershell
py C:\AMCTracker\tracker_multiwatch.py --health
```

`[OK]   Playwright installed` confirms the package is available.

> If `playwright install chromium` fails due to permissions, run the terminal as Administrator.

---

## Reinstall Python Dependencies

All dependencies are listed in `requirements.txt`.

**Install:**
```powershell
pip install -r C:\AMCTracker\requirements.txt
```

**Then reinstall Playwright browser (required separately):**
```powershell
playwright install chromium
```

**Verify:**
```powershell
py C:\AMCTracker\tracker_multiwatch.py --health
```

Both `[OK]   Playwright installed` and `[OK]   requests installed` should appear.

---

## Verify Health with --health

Run the health check at any time without contacting AMC or modifying files:

```powershell
py C:\AMCTracker\tracker_multiwatch.py --health
```

**Expected healthy output:**
```
[OK]   watchlist.json valid
[OK]   state.json valid
[OK]   tracker.log writable
[OK]   Playwright installed
[OK]   requests installed
[OK]   Pushover configured

Enabled watchlists  : 1
Disabled watchlists : 0

Overall status: HEALTHY
```

**Interpreting results:**

| Output | Meaning | Action |
|---|---|---|
| `[OK]` | Check passed | None |
| `[WARN] state.json not found` | No runs yet or deleted | Safe to ignore; tracker will create it |
| `[WARN] Pushover not configured` | Env vars missing | Set `PUSHOVER_USER_KEY` and `PUSHOVER_API_TOKEN` |
| `[FAIL] watchlist.json not found` | File missing | Restore from backup (see above) |
| `[FAIL] Playwright not installed` | Package missing | Reinstall Playwright (see above) |
| `Overall status: UNHEALTHY` | One or more failures | Address each `[FAIL]` item |

---

## Interpret Run Summary Failure Types

When a watchlist fails during a run, the console shows a labeled prefix instead of the generic `[ERROR]`:

| Label | Meaning | Action |
|---|---|---|
| `[CHALLENGE_PAGE]` | Cloudflare rate-limited the request (Error 1015) | Transient — wait for the next scheduled run; no action needed |
| `[EXPIRED_URL]` | Full page loaded but no seat data found | Showtime may be sold out or removed; verify the URL is still valid in AMC |
| `[PARSE_ERROR]` | seatingLayout found but JSON extraction failed | AMC may have changed their page structure; check `tracker.log` for the stack trace |
| `[PLAYWRIGHT_ERROR]` | Browser launch, navigation, or timeout failure | Check Playwright installation (`--health`); check network connectivity |

**CHALLENGE_PAGE is expected** under high-frequency manual testing (e.g., running the tracker multiple times in rapid succession). In scheduled cron operation each invocation starts fresh; Cloudflare rate limiting is rarely triggered.

**To see the full error detail for PARSE_ERROR or PLAYWRIGHT_ERROR:**
```powershell
Get-Content C:\AMCTracker\tracker.log -Tail 40
```
Both categories log at EXCEPTION level and include the full Python stack trace.

**Run summary sub-breakdown** appears when any watchlist failed:
```
  Failed             : 1
    Challenge/bot    : 1
    Expired URL      : 0
    Parse error      : 0
    Playwright error : 0
```

---

## Available Seats Visible in AMC but Not Detected

If the AMC website shows available (blue) seats but `--inspect` reports zero or very few available seats, work through these steps.

**Step 1 — Run `--inspect`:**

```powershell
py C:\AMCTracker\tracker_multiwatch.py --inspect INDEX
```

Check the **Available seats discovered** count in the summary. If it is much lower than the AMC UI suggests, the issue is in seat detection, not in watchlist configuration.

**Step 2 — Run `--diagnose-seat-types`:**

```powershell
py C:\AMCTracker\tracker_multiwatch.py --diagnose-seat-types INDEX
```

Review the **Counts by (type, available)** section for available seats under types other than `CanReserve`.

**Step 3 — Identify the cause:**

| Observation | Likely cause |
|---|---|
| `LoveSeatLeft / True` or `LoveSeatRight / True` count is large | Loveseat auditorium (expected — counted normally as of v1.0.3) |
| `production filter (RESERVABLE)` lower than `available is True` | Seat types outside `RESERVABLE_TYPES` are present |
| `available is True` count is low but AMC UI shows many seats | Partial hydration — RSC payload incomplete at capture time |
| Total seats collected far below expected auditorium size | Partial hydration |

**LoveSeat auditoriums:**
Loveseat theaters type all seats as `LoveSeatLeft` / `LoveSeatRight`. These are included in `RESERVABLE_TYPES` and counted normally as of v1.0.3. If running an older version, this produces false zero counts.

**Expected behavior:**
`Companion` and `Wheelchair` seats may appear available in AMC's UI but are intentionally excluded from tracker availability counts and notifications. Differences caused solely by `Companion` or `Wheelchair` inventory do not indicate a tracker malfunction.

**Partial hydration:**
If total seats collected is lower than expected or changes significantly between runs, the page may not be fully hydrated before capture. The fix in v1.0.3 (`wait_for_load_state("networkidle")`) addresses this. Run `--diagnose-layout INDEX` to count `seatingLayout` occurrences and compare seat totals across runs.

---

## Diagnose watch_adjacent Results

If `watch_adjacent` is producing unexpected results — notifications for windows you did not expect, or expected windows not triggering — use `--inspect` to see exactly what the live seat map shows without changing any state.

```powershell
py C:\AMCTracker\tracker_multiwatch.py --inspect 1
```

`--inspect` is fully read-only. It does not modify `state.json` or `watchlist.json`, does not update seat state, and does not send any notifications. It is safe to run at any time, including mid-session.

### Output sections

| Section | What it shows |
|---|---|
| All available seats | Every CanReserve seat currently available in the full layout |
| Adjacent windows (all rows) | All consecutive N-seat windows available anywhere in the layout, across all rows |
| Matching watchlist criteria | Windows available within your configured rows only, per `watch_adjacent` entry |
| Summary | Available seat count, total windows (all rows), windows matching watchlist criteria |

### Investigation Workflow

**Step 1** — Run `--inspect` for the watchlist showing unexpected behavior:
```powershell
py C:\AMCTracker\tracker_multiwatch.py --inspect 1
```

**Step 2** — Compare the two adjacency sections:
- **Adjacent windows (all rows)** shows every window the tracker can see in the layout
- **Matching watchlist criteria** shows only windows within your configured rows

If a window appears under **Adjacent windows (all rows)** but not under **Matching watchlist criteria**, the window's row is not listed in your `watch_adjacent` rows config.

**Step 3** — If a window appears under **Matching watchlist criteria** but no notification was sent, check `state.json` for the corresponding `adj:` key:
```powershell
py -c "import json; s=json.load(open('C:\AMCTracker\state.json')); [print(k,v) for k,v in s.items() if 'adj:' in str(k) or isinstance(v,dict) and any('adj:' in kk for kk in v)]"
```
A window stored as `AVAILABLE` in `state.json` from a prior run suppresses re-notification. Delete `state.json` to reset all state and re-trigger notifications on the next run.

---

## Test Notifications

**Send a test Pushover notification:**
```powershell
py C:\AMCTracker\tracker_multiwatch.py --test-notification
```

This sends a test message using the first watchlist's name as the title. Requires `PUSHOVER_USER_KEY` and `PUSHOVER_API_TOKEN` to be set.

**Verify env vars are set:**
```powershell
Write-Host "USER_KEY: $($env:PUSHOVER_USER_KEY.Length) chars"
Write-Host "API_TOKEN: $($env:PUSHOVER_API_TOKEN.Length) chars"
```

**Set env vars for the current session:**
```powershell
$env:PUSHOVER_USER_KEY = "your_user_key_here"
$env:PUSHOVER_API_TOKEN = "your_api_token_here"
```

**Set env vars permanently (System, requires admin):**
```powershell
[System.Environment]::SetEnvironmentVariable("PUSHOVER_USER_KEY", "your_user_key_here", "Machine")
[System.Environment]::SetEnvironmentVariable("PUSHOVER_API_TOKEN", "your_api_token_here", "Machine")
```

**Simulate a seat becoming available** (triggers real change detection and notification):
```powershell
py C:\AMCTracker\tracker_multiwatch.py --simulate-available J15
```

> After a `--simulate-available` run, delete `state.json` to reset it, otherwise the next real run will detect J15 reverting to UNAVAILABLE.

---

## Verify Scheduled Execution

AMCTracker is typically run via Windows Task Scheduler.

**Check if a scheduled task exists:**
```powershell
Get-ScheduledTask | Where-Object TaskName -like "*AMC*"
```

**Check the last run result:**
```powershell
Get-ScheduledTaskInfo -TaskName "AMCTracker" | Select-Object LastRunTime, LastTaskResult
```

A `LastTaskResult` of `0` means success.

**Manually trigger the scheduled task:**
```powershell
Start-ScheduledTask -TaskName "AMCTracker"
```

**Check the log to confirm the task ran:**
```powershell
Get-Content C:\AMCTracker\tracker.log -Tail 20
```

Look for `--- run started ---` and a `RUN SUMMARY` line near the end.

**If the task is missing or broken, recreate it** (adjust path and interval as needed):
```powershell
$action  = New-ScheduledTaskAction -Execute "py" -Argument "C:\AMCTracker\tracker_multiwatch.py" -WorkingDirectory "C:\AMCTracker"
$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 5) -Once -At (Get-Date)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 3)
Register-ScheduledTask -TaskName "AMCTracker" -Action $action -Trigger $trigger -Settings $settings
```

> Env vars (`PUSHOVER_USER_KEY`, `PUSHOVER_API_TOKEN`) must be set at the **System** level for the scheduled task to pick them up.

---

## Migrate AMCTracker to a New PC

### Step 1 — Copy files

Copy the entire `C:\AMCTracker` directory to the new machine. At minimum, transfer:

- `tracker_multiwatch.py`
- `watchlist.json`
- `state.json` (optional — safe to omit; tracker recreates it)
- `requirements.txt`
- `CLAUDE.md`
- `RECOVERY.md`
- `PROJECT_STATUS.md`

### Step 2 — Install Python

Download and install Python 3.11+ from [python.org](https://www.python.org/downloads/). Ensure `py` is on the PATH.

Verify:
```powershell
py --version
```

### Step 3 — Install Python dependencies

```powershell
pip install -r C:\AMCTracker\requirements.txt
```

### Step 4 — Install Playwright browser

```powershell
playwright install chromium
```

### Step 5 — Set environment variables

```powershell
[System.Environment]::SetEnvironmentVariable("PUSHOVER_USER_KEY", "your_user_key_here", "Machine")
[System.Environment]::SetEnvironmentVariable("PUSHOVER_API_TOKEN", "your_api_token_here", "Machine")
```

Open a new terminal after setting these.

### Step 6 — Verify health

```powershell
py C:\AMCTracker\tracker_multiwatch.py --health
```

All items should show `[OK]`. Pushover should show `[OK]   Pushover configured`.

### Step 7 — Test notification

```powershell
py C:\AMCTracker\tracker_multiwatch.py --test-notification
```

Confirm the Pushover alert arrives on your device.

### Step 8 — Run the tracker manually

```powershell
py C:\AMCTracker\tracker_multiwatch.py
```

Confirm seat statuses are printed and no errors occur.

### Step 9 — Recreate scheduled task (if needed)

See **Verify Scheduled Execution** above.

---

## Quick Reference

| Problem | Command |
|---|---|
| Check environment | `py tracker_multiwatch.py --health` |
| Test Pushover | `py tracker_multiwatch.py --test-notification` |
| Show watchlists | `py tracker_multiwatch.py --show-watchlists` |
| Restore watchlist.json | `Copy-Item watchlist.json.bak.* watchlist.json` |
| Reset state | `Remove-Item state.json` |
| Reinstall deps | `pip install -r requirements.txt` |
| Reinstall browser | `playwright install chromium` |
| Check recent log | `Get-Content tracker.log -Tail 30` |
