# File Concurrency Model

This document describes every persistent file used by AMCTracker, who reads and
writes each one, when those operations occur, what atomicity guarantees exist, and
what protects against corruption. It is intended for maintainers who need to reason
about concurrent access or add new file I/O to the system.

---

## Process model

AMCTracker runs as two distinct processes:

**API server** (`uvicorn` / `web/main.py`)
A long-lived FastAPI process. Handles HTTP requests, drives the scheduler, manages
the activity feed, and reads run results. Uses asyncio for concurrency; some
operations cross into threads via `asyncio.to_thread` or `threading.Lock`.

**Tracker subprocess** (`tracker_multiwatch.py`)
A short-lived child process spawned by the API server for each run. Reads
`watchlist.json` and `state.json` at startup, fetches pages, updates state, and
writes its result to `pending.json`. The API server spawns at most one tracker
subprocess at a time, enforced by `threading.Lock` in `TrackerRunner`.

The two processes do not share memory. All coordination happens through the files
described below.

---

## File inventory

### `watchlist.json`

| Property | Value |
|---|---|
| Location | `<project_root>/watchlist.json` |
| Writers | CLI only (`--add`, `--edit`, `--clone`, `--enable`, `--disable`, `--remove`) |
| Readers | Tracker subprocess (once, at startup); API server (per HTTP request via `WatchlistService`); API server at startup via `ensure_watchlist_ids` |

**When written:** Only by interactive CLI commands run on the Pi. Never by the API
server in the current codebase. Phase 4 will add API writes; see the edge-case note
below.

**When read:**
- Tracker subprocess: `load_watchlists()` is called once at the start of `main()`.
  The in-memory list is used for the entire run; changes made to the file during a
  run are not observed.
- API server: `WatchlistService` performs a fresh `json.loads(path.read_text(...))`
  on every `/api/v1/watchlists` or `/api/v1/watchlists/{id}` request. There is no
  cache.

**Atomicity:** CLI writes use `_write_watchlist_json`, which opens the file and
calls `json.dump()` directly — **not atomic**. A crash mid-write would corrupt the
file. A timestamped backup is always created immediately before the write, so
recovery is possible manually.

**Why corruption is unlikely in practice:** CLI commands are interactive and short;
the write window is milliseconds. The tracker subprocess and API server never write
this file, so there are no concurrent writers.

**Phase 4 note:** When API-driven writes are added (enable/disable/rename/clone/
delete), they must use `tmp.rename(target)` to be atomic. API writes must also be
rejected while a tracker subprocess is running, because the subprocess holds the
file's content in memory from startup and will overwrite the API's changes if it
also writes (Phase 2 auto-disable path).

---

### `state.json`

| Property | Value |
|---|---|
| Location | `<project_root>/state.json` |
| Writers | Tracker subprocess only |
| Readers | Tracker subprocess only |

**When written:** At the end of `main()`, after all watchlists have been checked,
via `save_state()`. Written once per run.

**When read:** At the start of `main()`, via `load_state()`. If the file does not
exist, an empty dict is returned and the tracker treats all seats as having no prior
state (no change notifications will fire for the first run).

**Atomicity:** `save_state()` writes to a `.json.tmp` sibling then calls
`tmp.replace(STATE_FILE)` — **atomic on Linux** (single `rename(2)` syscall).

**Concurrency:** The API server never reads or writes `state.json`. The tracker
subprocess is the sole accessor. No synchronization is needed.

**Phase 2 note:** Auto-disable logic will extend each watchlist's entry in
`state.json` with a `_meta` subkey for expiry tracking. This is backward-compatible:
existing seat-name keys (letters + digits) will never collide with `_meta`. The
atomicity guarantee is unchanged.

---

### `settings.json`

| Property | Value |
|---|---|
| Location | `web/data/settings.json` |
| Writers | API server only (`SettingsService._write`) |
| Readers | API server (per request via `SettingsService.load()`); tracker subprocess (at notification time via `_get_pushover_credentials`) |

**When written:** On `PUT /api/v1/settings`. `SettingsService._write` is the sole
code path.

**When read:**
- API server: `get_settings()` in `dependencies.py` calls `SettingsService.load()`
  on every request that declares `settings: BackendSettings = Depends(get_settings)`.
  There is no cache; every call reads from disk.
- Tracker subprocess: `_get_pushover_credentials()` reads the file at the moment a
  notification is about to be sent. This is the only field the tracker reads from
  this file; it falls back to environment variables first.

**Atomicity:** `SettingsService._write` uses `tmp.with_suffix(".tmp")` +
`tmp.replace(sf)` — **atomic**.

**Concurrency between API and tracker:** The API server is the sole writer. If the
API writes `settings.json` while the tracker subprocess is mid-run and about to read
it for credentials, the tracker will see either the old version or the new version
(never a partial write). Either is safe: old credentials still work; new credentials
take effect on the next notification within the same run.

---

### `pending.json`

| Property | Value |
|---|---|
| Location | `web/data/runs/pending.json` |
| Writers | Tracker subprocess (via `--json-output` flag) |
| Readers | API server (`TrackerRunner._process_output_file`), always after subprocess exits |

**When written:** The tracker subprocess writes its complete JSON run result to
this path via `write_json_output`, which calls `Path(path).write_text(...)` —
**not atomic**. The write happens once, at the very end of `main()`, after all
watchlists have been checked and state has been saved.

**When read:** `TrackerRunner._run_background` reads `pending.json` only inside
`_process_output_file`, which is called after `await proc.wait()` confirms the
subprocess has fully exited. The read is therefore always sequentially after the
write completes — there is no concurrent access.

**Lifecycle:**
1. Deleted at the start of each run (`pending_path.unlink(missing_ok=True)`).
2. Written by the tracker subprocess at the end of a successful run.
3. Read, validated, and moved to `web/data/runs/<run_id>.json` by the API server.
4. On any error path, deleted by the API server.

The file is never present between runs under normal operation.

---

### `web/data/runs/<run_id>.json` (history files)

| Property | Value |
|---|---|
| Location | `web/data/runs/<uuid>.json` |
| Writers | API server only (`TrackerRunner._process_output_file` via `shutil.move`) |
| Readers | API server (`HistoryService._load_result` on every history request) |

**When written:** Once, immediately after `pending.json` is validated. `shutil.move`
on Linux resolves to `os.rename` when source and destination are on the same
filesystem, which is the case on a Pi with a single partition — **effectively
atomic**.

**When read:** `HistoryService.get_all()` scans `web/data/runs/*.json` and reads
every UUID-named file on each `/api/v1/history` request. Files are read-only after
creation; they are never modified.

**Retention:** `HistoryService` sorts by `completed_at` and returns only the most
recent `max_history_runs` entries. Older files remain on disk but are excluded from
API responses. There is currently no automated pruning.

---

### `latest.json`

| Property | Value |
|---|---|
| Location | `web/data/runs/latest.json` |
| Writers | API server only (`TrackerRunner._process_output_file` via `shutil.copy2`) |
| Readers | API server (`RunService.get_latest` on every `/api/v1/runs/latest` request) |

**When written:** Immediately after the history file is written, via
`shutil.copy2(archive_path, latest_run_file)` — **not atomic**. `copy2` writes
to the destination path directly without a temp-file rename.

**Known race:** If a request arrives for `/api/v1/runs/latest` while `copy2` is in
progress, the reader may see a partially written file and `json.loads` will raise,
which `RunService.get_latest` will surface as a 500. This window is very small
(milliseconds), and the scheduler does not trigger runs at a rate that would make
this likely in practice. A future fix is to replace `shutil.copy2` with a
`tmp.replace()` pattern.

---

### `job_status.json`

| Property | Value |
|---|---|
| Location | `web/data/runs/job_status.json` |
| Writers | API server only (`TrackerRunner._write_status`) |
| Readers | API server (once at `TrackerRunner.__init__` startup) |

**When written:** On every job state transition (starting → running → finished/
failed/cancelled) and on every `[EVT]` progress event from the tracker. Potentially
dozens of writes per run.

**When read:** Once, at API server startup, to reconcile any interrupted run from a
prior server process. After that, state is managed entirely in the `_job` in-memory
attribute.

**Atomicity:** `_write_status` uses `tmp.with_suffix(".tmp")` + `tmp.replace(path)`
— **atomic**.

**Thread safety of `_job`:** `_write_status` can be called from the asyncio event
loop (during stdout drain) and from `cancel()`, which may be called from any HTTP
request handler thread. The `_job` attribute assignment (`self._job = ...`) is
protected by Python's GIL, which prevents torn reads or writes to the reference
itself. However, the read-modify-write sequence in `_set_job` is not wrapped in a
`threading.Lock`. Under current usage this is safe because `cancel()` replaces
`_job` wholesale and does not depend on reading the prior value first, but it is an
architectural assumption worth noting.

---

### `activity.json`

| Property | Value |
|---|---|
| Location | `web/data/activity.json` |
| Writers | API server only (`ActivityService._persist`) |
| Readers | API server (once at `ActivityService.__init__` startup) |

**When written:** On every event append — `run_start`, `watchlist_start`,
`watchlist_complete`, `notification_sent`, `scheduler_triggered`, etc. Each write
serializes the full in-memory deque (up to 500 events).

**When read:** Once, at API server startup, to reload the event history. After that,
all reads are served from the in-memory deque.

**Atomicity:** `_persist` uses `tmp.with_suffix(".tmp")` + `tmp.replace(path)` —
**atomic**.

**Thread safety:** `ActivityService` protects both the deque and the disk write with
a single `threading.Lock`. The lock is held for the duration of the disk write,
which serializes all concurrent appenders. On a Pi where disk I/O is slower than
RAM, this could briefly block callers during a busy run, but the event frequency is
low enough (one write per watchlist-level event) that this is not a concern.

---

### `scheduler_state.json`

| Property | Value |
|---|---|
| Location | `web/data/scheduler_state.json` |
| Writers | API server only (`SchedulerService._persist_state`) |
| Readers | API server (once at `SchedulerService.__init__` startup) |

**When written:** On every scheduler state change: when `next_run_at` is computed,
when a run fires (`last_triggered_at`), and when the scheduler is stopped or
reloaded.

**When read:** Once, at API server startup. After that, `_state` is managed in
memory; the file is the durability backing store so that `next_run_at` survives an
API server restart.

**Atomicity:** `_persist_state` uses `tmp.with_suffix(".tmp")` + `tmp.replace(path)`
— **atomic**.

**Concurrency:** `SchedulerService` runs entirely within the asyncio event loop and
has no thread-crossing methods. All state mutations occur in coroutines scheduled on
the same event loop thread. No additional locking is needed.

---

### `web/data/playwright/storage_state.json`

| Property | Value |
|---|---|
| Location | `web/data/playwright/storage_state.json` |
| Writers | Tracker subprocess only (`PlaywrightSession.save_storage_state`) |
| Readers | Tracker subprocess only (`PlaywrightSession._create_context`) |

**When written:** At the end of every successful run, inside `PlaywrightSession`'s
context while the browser is still open, via `path.write_text(...)` —
**not atomic**.

**When read:** At the start of every run, when `PlaywrightSession._create_context`
restores cookies and localStorage into the new browser context.

**Atomicity gap:** `write_text` is not atomic. If the tracker crashes mid-write,
`storage_state.json` may be corrupted. This is handled gracefully: `_create_context`
wraps the load in a try/except and falls back to a clean context if the file is
invalid. The next run will lose the session cookies but will otherwise succeed.

**Concurrency:** Only the tracker subprocess accesses this file, and only one tracker
subprocess runs at a time. There are no concurrent readers or writers.

---

## Summary table

| File | Writer | Atomic write | Concurrent readers |
|---|---|---|---|
| `watchlist.json` | CLI only | No (direct write) | API per-request; tracker at startup |
| `state.json` | Tracker only | Yes (`tmp.replace`) | None |
| `settings.json` | API only | Yes (`tmp.replace`) | API per-request; tracker at notification time |
| `pending.json` | Tracker only | No (direct write) | API, always after subprocess exit |
| `runs/<id>.json` | API only | Yes (same-fs `rename`) | API per-request |
| `latest.json` | API only | **No** (`shutil.copy2`) | API per-request |
| `job_status.json` | API only | Yes (`tmp.replace`) | None (startup only) |
| `activity.json` | API only | Yes (`tmp.replace`) | None (startup only) |
| `scheduler_state.json` | API only | Yes (`tmp.replace`) | None (startup only) |
| `storage_state.json` | Tracker only | No (direct write) | None (startup only) |

---

## Known atomicity gaps

### `latest.json` — `shutil.copy2` is not atomic

A concurrent HTTP request for `/api/v1/runs/latest` during a write will see a
partial file and receive a 500. The window is extremely narrow (milliseconds).
**Mitigation:** Replace `shutil.copy2` with a `tmp.replace()` pattern in
`TrackerRunner._process_output_file`.

### `watchlist.json` — CLI writes are not atomic

The `_write_watchlist_json` helper writes directly to the file. A crash mid-write
corrupts it. **Mitigation:** A timestamped backup is always created first, enabling
manual recovery. Phase 4 API writes will use atomic `tmp.replace()`.

### `storage_state.json` — `write_text` is not atomic

A tracker crash mid-write corrupts the file. **Mitigation:** `_create_context`
detects invalid files and falls back to a fresh context. No data loss beyond the
current session's cookies.

---

## Assumptions this model depends on

1. **Single tracker subprocess.** `threading.Lock` in `TrackerRunner` enforces
   mutual exclusion. If this lock were bypassed (e.g., a second API instance started
   without a process manager), multiple subprocesses could write `state.json`
   concurrently. The deployment assumes a single `uvicorn` process.

2. **Single filesystem.** `shutil.move` on same-filesystem paths resolves to
   `rename(2)`, which is atomic. On a Pi with a single partition this is always
   true. Cross-filesystem moves (e.g., if `web/data/` were a separate mount) would
   fall back to copy + delete.

3. **Linux filesystem semantics.** `rename(2)` atomicity is a POSIX guarantee that
   Linux upholds. This model does not hold on Windows (where `Path.replace()` is not
   guaranteed atomic) or on network filesystems (NFS, SMB) where `rename` atomicity
   is not guaranteed.

4. **No external writers.** No process outside this codebase modifies any of these
   files during normal operation. Manual edits (e.g., editing `watchlist.json` in a
   text editor via SSH) are safe only when the tracker subprocess is not running.
