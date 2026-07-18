import json

from pydantic import ValidationError

from web.config.exceptions import NoRunsYetError, RunOutputInvalidError
from web.config.paths import ProjectPaths
from web.models.job_status import JobStatus
from web.models.run_result import RunResult
from web.models.settings import BackendSettings
from web.services.tracker_runner import TrackerRunner


class RunService:
    def __init__(self, paths: ProjectPaths, settings: BackendSettings, runner: TrackerRunner):
        self._paths = paths
        self._settings = settings
        self._runner = runner

    async def launch_background(self) -> None:
        await self._runner.launch_background(self._settings)

    def cancel(self) -> bool:
        return self._runner.cancel()

    @property
    def job_status(self) -> JobStatus:
        return self._runner.job_status

    def get_latest(self) -> RunResult:
        wf = self._paths.latest_run_file
        if not wf.is_file():
            raise NoRunsYetError()
        try:
            raw = json.loads(wf.read_text(encoding="utf-8"))
            return RunResult.model_validate(raw)
        except ValidationError as e:
            raise RunOutputInvalidError(detail=f"latest.json validation failed: {e}")
        except Exception as e:
            raise RunOutputInvalidError(detail=f"Cannot read latest.json: {e}")
