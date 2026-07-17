import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from web.config.exceptions import HistoryRunNotFoundError, RunOutputInvalidError
from web.config.paths import ProjectPaths
from web.models.history import HistoryResponse, RunHistorySummary
from web.models.run_result import RunResult
from web.models.settings import BackendSettings

logger = logging.getLogger("amctracker.api")


class HistoryService:
    # Phase 1A: every request reads and validates all archived JSON files from disk.
    # This is intentional while max_history_runs stays small (default 50).
    # If history grows substantially, consider a pre-built index or sqlite database.

    def __init__(self, paths: ProjectPaths, settings: BackendSettings):
        self._paths = paths
        self._settings = settings

    def get_all(self) -> HistoryResponse:
        runs_dir = self._paths.runs_dir
        if not runs_dir.is_dir():
            return HistoryResponse(runs=[], skipped_files=[])

        summaries: list[RunHistorySummary] = []
        skipped: list[str] = []

        for path in runs_dir.glob("*.json"):
            try:
                uuid.UUID(path.stem)
            except ValueError:
                continue  # latest.json, pending.json, and any non-UUID files

            result = self._load_result(path)
            if result is None:
                skipped.append(path.name)
                continue
            summaries.append(RunHistorySummary.from_run_result(result))

        summaries.sort(key=lambda s: self._parse_dt(s.completed_at), reverse=True)
        summaries = summaries[: self._settings.max_history_runs]

        return HistoryResponse(runs=summaries, skipped_files=sorted(skipped))

    def get_by_id(self, run_id: uuid.UUID) -> RunResult:
        path = self._paths.runs_dir / f"{run_id}.json"
        if not path.is_file():
            raise HistoryRunNotFoundError(run_id)
        result = self._load_result(path)
        if result is None:
            raise RunOutputInvalidError(detail=f"Archived run {run_id} failed validation")
        return result

    def _load_result(self, path: Path) -> RunResult | None:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return RunResult.model_validate(raw)
        except Exception as exc:
            logger.warning("Skipping corrupted history file %s: %s", path.name, exc)
            return None

    @staticmethod
    def _parse_dt(ts: str) -> datetime:
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            return datetime.min
