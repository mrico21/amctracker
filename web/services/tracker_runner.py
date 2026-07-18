import asyncio
import json
import logging
import shutil
import subprocess
import threading

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
from web.models.run_result import RunResult
from web.models.settings import BackendSettings
from web.models.tracker_run import TrackerRunRequest

logger = logging.getLogger("amctracker.api")


def _d(msg: str) -> None:
    logger.warning(msg)
    print(msg, flush=True)


class TrackerRunner:
    def __init__(self, paths: ProjectPaths):
        self._paths = paths
        self._lock = threading.Lock()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    async def execute(self, settings: BackendSettings) -> RunResult:
        _d("[DIAG] execute() entered — attempting lock acquire")
        if not self._lock.acquire(blocking=False):
            _d("[DIAG] execute() lock busy — raising RunAlreadyInProgressError")
            raise RunAlreadyInProgressError()
        _d("[DIAG] execute() lock acquired")
        self._running = True
        try:
            _d("[DIAG] execute() building TrackerRunRequest")
            request = TrackerRunRequest(
                python_executable=settings.python_executable,
                tracker_script=self._paths.tracker_script,
                tracker_root=self._paths.tracker_root,
                runs_dir=self._paths.runs_dir,
                latest_run_file=self._paths.latest_run_file,
                timeout_seconds=settings.run_timeout_seconds,
            )
            _d("[DIAG] execute() TrackerRunRequest built — calling asyncio.to_thread")
            result = await asyncio.to_thread(self._run_sync, request)
            _d("[DIAG] execute() asyncio.to_thread returned")
            return result
        finally:
            self._running = False
            self._lock.release()
            _d("[DIAG] execute() lock released")

    def _run_sync(self, request: TrackerRunRequest) -> RunResult:
        _d("[DIAG] _run_sync() entered")
        pending_path = request.runs_dir / "pending.json"

        _d(f"[DIAG] _run_sync() clearing pending.json at {pending_path}")
        # Clear any leftover from a previously crashed run
        pending_path.unlink(missing_ok=True)
        _d("[DIAG] _run_sync() pending.json cleared")

        _d(f"[DIAG] _run_sync() checking tracker script exists: {request.tracker_script}")
        # Verify tracker script exists before attempting launch
        if not request.tracker_script.is_file():
            _d("[DIAG] _run_sync() tracker script NOT FOUND — raising TrackerNotFoundError")
            raise TrackerNotFoundError()
        _d("[DIAG] _run_sync() tracker script found")

        # Build command — str() conversions only here for subprocess
        cmd = [
            request.python_executable,
            str(request.tracker_script),
            "--json-output",
            str(pending_path),
        ]
        _d(f"[DIAG] _run_sync() cmd built: {cmd}")

        # Launch subprocess
        _d(f"[DIAG] _run_sync() calling subprocess.run (timeout={request.timeout_seconds}s)")
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                cwd=str(request.tracker_root),
            )
        except subprocess.TimeoutExpired:
            _d("[DIAG] _run_sync() subprocess TIMED OUT")
            pending_path.unlink(missing_ok=True)
            raise TrackerTimeoutError(timeout_seconds=request.timeout_seconds)
        except OSError as e:
            _d(f"[DIAG] _run_sync() subprocess OSError: {e}")
            raise TrackerLaunchError(detail=str(e))
        _d(f"[DIAG] _run_sync() subprocess.run returned — returncode={proc.returncode}")

        # Log stdout and stderr — informational only, never parsed
        _d(f"[DIAG] _run_sync() stdout len={len(proc.stdout)}, stderr len={len(proc.stderr)}")
        if proc.stdout:
            logger.info("tracker stdout:\n%s", proc.stdout.rstrip())
        if proc.stderr:
            if proc.returncode == 0:
                logger.info("tracker stderr:\n%s", proc.stderr.rstrip())
            else:
                logger.warning("tracker stderr:\n%s", proc.stderr.rstrip())

        if proc.returncode != 0:
            _d(f"[DIAG] _run_sync() non-zero returncode {proc.returncode} — raising TrackerExecutionError")
            pending_path.unlink(missing_ok=True)
            raise TrackerExecutionError(exit_code=proc.returncode, stderr=proc.stderr)

        _d("[DIAG] _run_sync() returncode==0 — checking pending.json exists")
        # Verify output file was created
        if not pending_path.is_file():
            _d("[DIAG] _run_sync() pending.json MISSING — raising RunOutputMissingError")
            raise RunOutputMissingError()
        _d("[DIAG] _run_sync() pending.json exists — parsing JSON")

        # Parse JSON
        try:
            raw = json.loads(pending_path.read_text(encoding="utf-8"))
        except Exception as e:
            _d(f"[DIAG] _run_sync() JSON parse FAILED: {e}")
            pending_path.unlink(missing_ok=True)
            raise RunOutputInvalidError(detail=f"Cannot parse JSON: {e}")
        _d("[DIAG] _run_sync() JSON parsed — checking schema_version")

        # Validate schema version before full model validation
        if raw.get("schema_version") != 1:
            _d(f"[DIAG] _run_sync() bad schema_version: {raw.get('schema_version')}")
            pending_path.unlink(missing_ok=True)
            raise RunOutputInvalidError(
                detail=f"Unexpected schema_version: {raw.get('schema_version')}"
            )
        _d("[DIAG] _run_sync() schema_version OK — calling RunResult.model_validate")

        # Validate against frozen RunResult model
        try:
            result = RunResult.model_validate(raw)
        except ValidationError as e:
            _d(f"[DIAG] _run_sync() RunResult validation FAILED: {e}")
            pending_path.unlink(missing_ok=True)
            raise RunOutputInvalidError(detail=f"RunResult validation failed: {e}")
        _d(f"[DIAG] _run_sync() RunResult validated — run_id={result.run_id}")

        # Archive: pending.json → {run_id}.json
        archive_path = request.runs_dir / f"{result.run_id}.json"
        _d(f"[DIAG] _run_sync() archiving pending.json -> {archive_path}")
        try:
            shutil.move(pending_path, archive_path)
        except Exception as e:
            _d(f"[DIAG] _run_sync() archive FAILED: {e} — returning result without archive")
            logger.error("Failed to archive run output to %s: %s", archive_path, e)
            pending_path.unlink(missing_ok=True)
            return result
        _d("[DIAG] _run_sync() archived — updating latest.json")

        # Update latest.json
        try:
            shutil.copy2(archive_path, request.latest_run_file)
        except Exception as e:
            _d(f"[DIAG] _run_sync() latest.json update FAILED: {e}")
            logger.error("Failed to update latest.json: %s", e)
        _d("[DIAG] _run_sync() latest.json updated — returning result")

        return result
