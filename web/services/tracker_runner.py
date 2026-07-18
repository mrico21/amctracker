import asyncio
import json
import logging
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from web.config.exceptions import (
    RunAlreadyInProgressError,
    RunOutputInvalidError,
    RunOutputMissingError,
    TrackerExecutionError,
    TrackerLaunchError,
    TrackerNotFoundError,
    TrackerTimeoutError,
)
from web.config.paths import ProjectPaths
from web.models.activity import ActivityEvent
from web.models.job_status import JobStatus
from web.models.run_result import RunResult
from web.models.settings import BackendSettings
from web.models.tracker_run import TrackerRunRequest
from web.services.activity_service import ActivityService

logger = logging.getLogger("amctracker.api")


class TrackerRunner:
    def __init__(self, paths: ProjectPaths, activity: ActivityService):
        self._paths = paths
        self._activity = activity
        self._lock = threading.Lock()
        self._proc: asyncio.subprocess.Process | None = None
        self._job: JobStatus = self._load_persisted_status()
        self._current_run_id: str | None = None

    # ── Startup reconciliation ────────────────────────────────────────────────

    def _load_persisted_status(self) -> JobStatus:
        path = self._paths.job_status_file
        if not path.is_file():
            return JobStatus()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            status = JobStatus.model_validate(data)
            if status.status in ("starting", "running"):
                status = status.model_copy(update={
                    "status": "failed",
                    "error_message": "Run interrupted by API restart",
                })
                self._write_status(status)
            return status
        except Exception as e:
            logger.warning("Could not load job_status.json: %s", e)
            return JobStatus()

    # ── Public properties ─────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._job.status in ("starting", "running")

    @property
    def job_status(self) -> JobStatus:
        job = self._job
        if job.status in ("starting", "running") and job.started_at:
            started = datetime.fromisoformat(job.started_at)
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            return job.model_copy(update={"elapsed_seconds": round(elapsed, 1)})
        return job

    # ── Launch / cancel ───────────────────────────────────────────────────────

    async def launch_background(
        self,
        settings: BackendSettings,
        trigger_type: str = "manual",
    ) -> None:
        if not self._lock.acquire(blocking=False):
            raise RunAlreadyInProgressError()

        self._set_job(
            status="starting",
            run_id=None,
            started_at=datetime.now(timezone.utc).isoformat(),
            elapsed_seconds=0.0,
            current_watchlist=None,
            completed_watchlists=0,
            total_watchlists=0,
            error_message=None,
            trigger_type=trigger_type,
        )

        request = TrackerRunRequest(
            python_executable=settings.python_executable,
            tracker_script=self._paths.tracker_script,
            tracker_root=self._paths.tracker_root,
            runs_dir=self._paths.runs_dir,
            latest_run_file=self._paths.latest_run_file,
            timeout_seconds=settings.run_timeout_seconds,
            randomize_order=settings.scheduler_randomize_order,
        )

        asyncio.create_task(self._run_background(request))

    def cancel(self) -> bool:
        if self._job.status not in ("starting", "running"):
            return False
        run_id = self._current_run_id
        self._set_job(status="cancelled", error_message="Run was cancelled by user")
        proc = self._proc
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass
        self._activity.make_and_append(
            event_type="run_cancelled",
            message="Run cancelled by user",
            payload={},
            run_id=run_id,
        )
        return True

    # ── Background task ───────────────────────────────────────────────────────

    async def _run_background(self, request: TrackerRunRequest) -> None:
        pending_path = request.runs_dir / "pending.json"
        pending_path.unlink(missing_ok=True)

        try:
            if not request.tracker_script.is_file():
                raise TrackerNotFoundError()

            self._set_job(status="running")

            cmd = [
                request.python_executable,
                str(request.tracker_script),
                "--json-output",
                str(pending_path),
            ]
            if request.randomize_order:
                cmd.append("--randomize-order")

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(request.tracker_root),
                )
            except OSError as e:
                raise TrackerLaunchError(detail=str(e))

            self._proc = proc

            timed_out = False
            try:
                await asyncio.wait_for(
                    self._drain_stdout(proc),
                    timeout=float(request.timeout_seconds),
                )
            except asyncio.TimeoutError:
                timed_out = True
                proc.kill()
                try:
                    async for _ in proc.stdout:
                        pass
                except Exception:
                    pass

            stderr_bytes = await proc.stderr.read()
            await proc.wait()
            self._proc = None

            if timed_out:
                raise TrackerTimeoutError(timeout_seconds=request.timeout_seconds)

            returncode = proc.returncode
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            if returncode != 0:
                if self._job.status == "cancelled":
                    return
                pending_path.unlink(missing_ok=True)
                raise TrackerExecutionError(exit_code=returncode, stderr=stderr)

            result = await asyncio.to_thread(
                self._process_output_file, pending_path, request
            )

            if self._job.status != "cancelled":
                self._set_job(
                    status="finished",
                    run_id=result.run_id,
                    current_watchlist=None,
                )

        except TrackerTimeoutError as e:
            if self._job.status != "cancelled":
                self._set_job(
                    status="failed",
                    error_message=f"Tracker timed out after {e.timeout_seconds}s",
                )
        except TrackerNotFoundError:
            self._set_job(status="failed", error_message="Tracker script not found")
        except TrackerLaunchError as e:
            self._set_job(status="failed", error_message=f"Failed to launch tracker: {e.detail}")
        except TrackerExecutionError as e:
            self._set_job(status="failed", error_message=f"Tracker exited with code {e.exit_code}")
        except RunOutputMissingError:
            self._set_job(status="failed", error_message="Tracker produced no output")
        except RunOutputInvalidError as e:
            self._set_job(status="failed", error_message=f"Invalid tracker output: {e.detail}")
        except Exception as e:
            if self._job.status not in ("cancelled",):
                self._set_job(status="failed", error_message=str(e))
            logger.exception("Unexpected error in background run: %s", e)
        finally:
            self._proc = None
            self._lock.release()

    async def _drain_stdout(self, proc: asyncio.subprocess.Process) -> None:
        async for line_bytes in proc.stdout:
            line = line_bytes.decode("utf-8", errors="replace").rstrip("\n")
            logger.info("tracker: %s", line)
            self._parse_evt_line(line)

    # ── Output file processing (runs in thread) ───────────────────────────────

    def _process_output_file(
        self, pending_path: Path, request: TrackerRunRequest
    ) -> RunResult:
        if not pending_path.is_file():
            raise RunOutputMissingError()

        try:
            raw = json.loads(pending_path.read_text(encoding="utf-8"))
        except Exception as e:
            pending_path.unlink(missing_ok=True)
            raise RunOutputInvalidError(detail=f"Cannot parse JSON: {e}")

        if raw.get("schema_version") != 1:
            pending_path.unlink(missing_ok=True)
            raise RunOutputInvalidError(
                detail=f"Unexpected schema_version: {raw.get('schema_version')}"
            )

        try:
            result = RunResult.model_validate(raw)
        except ValidationError as e:
            pending_path.unlink(missing_ok=True)
            raise RunOutputInvalidError(detail=f"RunResult validation failed: {e}")

        archive_path = request.runs_dir / f"{result.run_id}.json"
        try:
            shutil.move(pending_path, archive_path)
        except Exception as e:
            logger.error("Failed to archive run output to %s: %s", archive_path, e)
            pending_path.unlink(missing_ok=True)
            return result

        try:
            shutil.copy2(archive_path, request.latest_run_file)
        except Exception as e:
            logger.error("Failed to update latest.json: %s", e)

        return result

    # ── Event protocol parser ─────────────────────────────────────────────────

    def _parse_evt_line(self, line: str) -> None:
        if not line.startswith("[EVT] "):
            return
        try:
            payload = json.loads(line[6:])
        except Exception:
            return

        evt_type = payload.get("type")
        run_id = payload.get("run_id") or self._current_run_id

        if evt_type == "run_start":
            self._current_run_id = payload.get("run_id")
            self._set_job(total_watchlists=payload.get("total_watchlists", 0))
            n = payload.get("total_watchlists", 0)
            self._activity.make_and_append(
                event_type="run_start",
                message=f"Run started - checking {n} watchlist{'s' if n != 1 else ''}",
                payload=payload,
                run_id=run_id,
            )

        elif evt_type == "watchlist_start":
            idx = payload.get("index", 0)
            total = payload.get("total", 0)
            name = payload.get("name", "")
            self._set_job(
                completed_watchlists=max(0, idx - 1),
                total_watchlists=total,
                current_watchlist=name,
            )
            self._activity.make_and_append(
                event_type="watchlist_start",
                message=f"Checking {name} ({idx}/{total})",
                payload=payload,
                run_id=run_id,
            )

        elif evt_type == "watchlist_complete":
            name = payload.get("watchlist", "")
            available_seats: list[str] = payload.get("available_seats", [])
            available_windows: list[str] = payload.get("available_windows", [])
            parts: list[str] = []
            if available_seats:
                parts.append(", ".join(available_seats))
            if available_windows:
                parts.append("adj: " + ", ".join(available_windows))
            detail = " - " + "; ".join(parts) if parts else " - no seats available"
            self._activity.make_and_append(
                event_type="watchlist_complete",
                message=f"{name}{detail}",
                payload=payload,
                run_id=run_id,
            )

        elif evt_type == "watchlist_blocked":
            name = payload.get("watchlist", "")
            self._activity.make_and_append(
                event_type="watchlist_blocked",
                message=f"Cloudflare block - {name}",
                payload=payload,
                run_id=run_id,
            )

        elif evt_type == "watchlist_failed":
            name = payload.get("watchlist", "")
            ft = payload.get("failure_type", "error").lower().replace("_", " ")
            self._activity.make_and_append(
                event_type="watchlist_failed",
                message=f"Failed ({ft}) - {name}",
                payload=payload,
                run_id=run_id,
            )

        elif evt_type == "notification_sent":
            name = payload.get("watchlist", "")
            seats: list[str] = payload.get("seats", [])
            seat_str = ", ".join(seats) if seats else "unknown"
            self._activity.make_and_append(
                event_type="notification_sent",
                message=f"Notification sent - {name}: {seat_str}",
                payload=payload,
                run_id=run_id,
            )

        elif evt_type == "run_complete":
            succeeded = payload.get("succeeded", 0)
            failed = payload.get("failed", 0)
            notifications = payload.get("notifications", 0)
            notif_str = (
                f", {notifications} notification{'s' if notifications != 1 else ''}"
                if notifications else ""
            )
            self._set_job(
                current_watchlist=None,
                completed_watchlists=succeeded + failed,
            )
            self._activity.make_and_append(
                event_type="run_complete",
                message=f"Run complete - {succeeded} succeeded, {failed} failed{notif_str}",
                payload=payload,
                run_id=run_id,
            )
            self._current_run_id = None

    # ── Internal state helpers ────────────────────────────────────────────────

    def _set_job(self, **kwargs) -> None:
        self._job = self._job.model_copy(update=kwargs)
        self._write_status(self._job)

    def _write_status(self, status: JobStatus) -> None:
        try:
            path = self._paths.job_status_file
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(status.model_dump_json(indent=2), encoding="utf-8")
            tmp.replace(path)
        except Exception as e:
            logger.warning("Failed to write job_status.json: %s", e)
