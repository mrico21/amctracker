import json
import socket
import subprocess
from datetime import datetime, timezone

from web.config.paths import ProjectPaths
from web.models.info import InfoResponse


def _read_git_hash() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


# Captured once at import time — stable for the lifetime of the server process
_GIT_HASH = _read_git_hash()
_SERVER_STARTED_AT = datetime.now(timezone.utc).isoformat()


class InfoService:
    _API_VERSION = "1"
    _SCHEMA_VERSION = 1

    def __init__(self, paths: ProjectPaths):
        self._paths = paths

    def get_info(self, is_running: bool) -> InfoResponse:
        tracker_version = None
        last_run_id = None
        last_run_status = None
        last_run_at = None

        try:
            if self._paths.latest_run_file.is_file():
                data = json.loads(
                    self._paths.latest_run_file.read_text(encoding="utf-8")
                )
                tracker_version = data.get("tracker_version")
                last_run_id = data.get("run_id")
                last_run_status = data.get("run_status")
                last_run_at = data.get("completed_at")
        except Exception:
            pass

        return InfoResponse(
            api_version=self._API_VERSION,
            schema_version=self._SCHEMA_VERSION,
            hostname=socket.gethostname(),
            run_in_progress=is_running,
            tracker_version=tracker_version,
            last_run_id=last_run_id,
            last_run_status=last_run_status,
            last_run_at=last_run_at,
            commit_hash=_GIT_HASH,
            server_started_at=_SERVER_STARTED_AT,
        )
