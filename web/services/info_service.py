import json
import socket

from web.config.paths import ProjectPaths
from web.models.info import InfoResponse


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
        )
