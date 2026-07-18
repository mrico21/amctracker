import json

from web.config.paths import ProjectPaths
from web.models.settings import BackendSettings, SettingsResponse, SettingsUpdate


class SettingsService:
    def __init__(self, paths: ProjectPaths):
        self._paths = paths

    def load(self) -> BackendSettings:
        sf = self._paths.settings_file
        if not sf.exists():
            defaults = BackendSettings()
            self._write(defaults)
            return defaults
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
            return BackendSettings(**data)
        except Exception:
            return BackendSettings()

    def save(self, data: BackendSettings) -> None:
        self._write(data)

    def update(self, update: SettingsUpdate) -> None:
        current = self.load()
        merged = BackendSettings(
            run_timeout_seconds=update.run_timeout_seconds,
            max_history_runs=update.max_history_runs,
            python_executable=update.python_executable,
            cors_origins=update.cors_origins,
            pushover_user_key=update.pushover_user_key,
            pushover_api_token=update.pushover_api_token,
        )
        # Preserve python_executable default logic from model_validator
        _ = current  # current values replaced wholesale by the update
        self._write(merged)

    def _write(self, data: BackendSettings) -> None:
        sf = self._paths.settings_file
        sf.parent.mkdir(parents=True, exist_ok=True)
        tmp = sf.with_suffix(".tmp")
        tmp.write_text(data.model_dump_json(indent=2), encoding="utf-8")
        tmp.replace(sf)

    def get_response(self) -> SettingsResponse:
        s = self.load()
        return SettingsResponse(
            run_timeout_seconds=s.run_timeout_seconds,
            max_history_runs=s.max_history_runs,
            python_executable=s.python_executable,
            cors_origins=s.cors_origins,
            pushover_user_key=s.pushover_user_key,
            pushover_api_token=s.pushover_api_token,
            tracker_script=str(self._paths.tracker_script),
            watchlist_file=str(self._paths.watchlist_file),
        )
