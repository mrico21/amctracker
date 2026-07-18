import sys

from pydantic import BaseModel, model_validator


class BackendSettings(BaseModel):
    run_timeout_seconds: int = 900  # DIAG: temporarily increased from 300
    max_history_runs: int = 50
    python_executable: str = ""
    cors_origins: list[str] = ["*"]
    pushover_user_key: str = ""
    pushover_api_token: str = ""
    scheduler_enabled: bool = False
    scheduler_min_interval_seconds: int = 600
    scheduler_max_interval_seconds: int = 1800
    scheduler_quiet_hours_enabled: bool = False
    scheduler_quiet_hours_start: str = "23:00"
    scheduler_quiet_hours_end: str = "07:00"
    scheduler_randomize_order: bool = False

    @model_validator(mode="after")
    def fill_python_default(self) -> "BackendSettings":
        is_windows = sys.platform == "win32"
        # Treat empty or Windows-only "py" launcher as "needs platform default"
        needs_default = not self.python_executable or (
            not is_windows and self.python_executable == "py"
        )
        if needs_default:
            self.python_executable = "py" if is_windows else sys.executable
        return self


class SettingsUpdate(BaseModel):
    run_timeout_seconds: int
    max_history_runs: int
    python_executable: str
    cors_origins: list[str]
    pushover_user_key: str = ""
    pushover_api_token: str = ""
    scheduler_enabled: bool = False
    scheduler_min_interval_seconds: int = 600
    scheduler_max_interval_seconds: int = 1800
    scheduler_quiet_hours_enabled: bool = False
    scheduler_quiet_hours_start: str = "23:00"
    scheduler_quiet_hours_end: str = "07:00"
    scheduler_randomize_order: bool = False


class SettingsResponse(BaseModel):
    run_timeout_seconds: int
    max_history_runs: int
    python_executable: str
    cors_origins: list[str]
    pushover_user_key: str
    pushover_api_token: str
    tracker_script: str
    watchlist_file: str
    scheduler_enabled: bool
    scheduler_min_interval_seconds: int
    scheduler_max_interval_seconds: int
    scheduler_quiet_hours_enabled: bool
    scheduler_quiet_hours_start: str
    scheduler_quiet_hours_end: str
    scheduler_randomize_order: bool
