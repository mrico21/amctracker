import json
import shutil
import uuid

from web.config.paths import ProjectPaths
from web.models.health import HealthCheckResult, HealthResponse
from web.models.settings import BackendSettings


class HealthService:
    def __init__(self, paths: ProjectPaths, settings: BackendSettings):
        self._paths = paths
        self._settings = settings

    def check(self) -> HealthResponse:
        checks = {
            "tracker_script": self._check_tracker_script(),
            "watchlist_file": self._check_watchlist_file(),
            "runs_dir": self._check_runs_dir(),
            "python_executable": self._check_python_executable(),
        }
        all_ok = all(c.status == "ok" for c in checks.values())
        return HealthResponse(
            status="healthy" if all_ok else "unhealthy",
            checks=checks,
        )

    def _check_tracker_script(self) -> HealthCheckResult:
        if self._paths.tracker_script.is_file():
            return HealthCheckResult(status="ok", detail=None)
        return HealthCheckResult(
            status="error",
            detail=f"File not found: {self._paths.tracker_script}",
        )

    def _check_watchlist_file(self) -> HealthCheckResult:
        p = self._paths.watchlist_file
        if not p.is_file():
            return HealthCheckResult(status="error", detail=f"File not found: {p}")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if "watchlists" not in data:
                return HealthCheckResult(status="error", detail="Missing 'watchlists' key")
            return HealthCheckResult(status="ok", detail=None)
        except Exception as e:
            return HealthCheckResult(status="error", detail=str(e))

    def _check_runs_dir(self) -> HealthCheckResult:
        d = self._paths.runs_dir
        if not d.is_dir():
            return HealthCheckResult(status="error", detail=f"Directory not found: {d}")
        probe = d / f".probe_{uuid.uuid4().hex}"
        try:
            probe.write_text("probe", encoding="utf-8")
            probe.unlink()
            return HealthCheckResult(status="ok", detail=None)
        except Exception as e:
            return HealthCheckResult(status="error", detail=f"Not writable: {e}")

    def _check_python_executable(self) -> HealthCheckResult:
        exe = self._settings.python_executable
        if shutil.which(exe) is not None:
            return HealthCheckResult(status="ok", detail=None)
        return HealthCheckResult(
            status="error",
            detail=f"Not found on PATH: {exe}",
        )
