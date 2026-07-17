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


class TrackerRunner:
    def __init__(self, paths: ProjectPaths):
        self._paths = paths
        self._lock = threading.Lock()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    async def execute(self, settings: BackendSettings) -> RunResult:
        if not self._lock.acquire(blocking=False):
            raise RunAlreadyInProgressError()
        self._running = True
        try:
            request = TrackerRunRequest(
                python_executable=settings.python_executable,
                tracker_script=self._paths.tracker_script,
                tracker_root=self._paths.tracker_root,
                runs_dir=self._paths.runs_dir,
                latest_run_file=self._paths.latest_run_file,
                timeout_seconds=settings.run_timeout_seconds,
            )
            return await asyncio.to_thread(self._run_sync, request)
        finally:
            self._running = False
            self._lock.release()

    def _run_sync(self, request: TrackerRunRequest) -> RunResult:
        pending_path = request.runs_dir / "pending.json"

        # Clear any leftover from a previously crashed run
        pending_path.unlink(missing_ok=True)

        # Verify tracker script exists before attempting launch
        if not request.tracker_script.is_file():
            raise TrackerNotFoundError()

        # Build command — str() conversions only here for subprocess
        cmd = [
            request.python_executable,
            str(request.tracker_script),
            "--json-output",
            str(pending_path),
        ]

        # Launch subprocess
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                cwd=str(request.tracker_root),
            )
        except subprocess.TimeoutExpired:
            pending_path.unlink(missing_ok=True)
            raise TrackerTimeoutError(timeout_seconds=request.timeout_seconds)
        except OSError as e:
            raise TrackerLaunchError(detail=str(e))

        # Log stdout and stderr — informational only, never parsed
        if proc.stdout:
            logger.info("tracker stdout:\n%s", proc.stdout.rstrip())
        if proc.stderr:
            if proc.returncode == 0:
                logger.info("tracker stderr:\n%s", proc.stderr.rstrip())
            else:
                logger.warning("tracker stderr:\n%s", proc.stderr.rstrip())

        if proc.returncode != 0:
            pending_path.unlink(missing_ok=True)
            raise TrackerExecutionError(exit_code=proc.returncode, stderr=proc.stderr)

        # Verify output file was created
        if not pending_path.is_file():
            raise RunOutputMissingError()

        # Parse JSON
        try:
            raw = json.loads(pending_path.read_text(encoding="utf-8"))
        except Exception as e:
            pending_path.unlink(missing_ok=True)
            raise RunOutputInvalidError(detail=f"Cannot parse JSON: {e}")

        # Validate schema version before full model validation
        if raw.get("schema_version") != 1:
            pending_path.unlink(missing_ok=True)
            raise RunOutputInvalidError(
                detail=f"Unexpected schema_version: {raw.get('schema_version')}"
            )

        # Validate against frozen RunResult model
        try:
            result = RunResult.model_validate(raw)
        except ValidationError as e:
            pending_path.unlink(missing_ok=True)
            raise RunOutputInvalidError(detail=f"RunResult validation failed: {e}")

        # Archive: pending.json → {run_id}.json
        archive_path = request.runs_dir / f"{result.run_id}.json"
        try:
            shutil.move(pending_path, archive_path)
        except Exception as e:
            logger.error("Failed to archive run output to %s: %s", archive_path, e)
            pending_path.unlink(missing_ok=True)
            return result

        # Update latest.json
        try:
            shutil.copy2(archive_path, request.latest_run_file)
        except Exception as e:
            logger.error("Failed to update latest.json: %s", e)

        return result
