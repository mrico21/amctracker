import sys
from datetime import time as dtime

from pydantic import BaseModel, model_validator


class BackendSettings(BaseModel):
    run_timeout_seconds: int = 600
    max_history_runs: int = 50
    python_executable: str = ""
    cors_origins: list[str] = ["*"]  # intentional: Pi is accessed from multiple devices on a private home network
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


def _valid_hhmm(value: str) -> bool:
    try:
        dtime.fromisoformat(value)
        return True
    except ValueError:
        return False


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

    @model_validator(mode="after")
    def validate_scheduler_intervals(self) -> "SettingsUpdate":
        if self.scheduler_min_interval_seconds > self.scheduler_max_interval_seconds:
            raise ValueError(
                f"scheduler_min_interval_seconds ({self.scheduler_min_interval_seconds}) "
                f"must not exceed scheduler_max_interval_seconds ({self.scheduler_max_interval_seconds})"
            )
        for field, value in [
            ("scheduler_quiet_hours_start", self.scheduler_quiet_hours_start),
            ("scheduler_quiet_hours_end", self.scheduler_quiet_hours_end),
        ]:
            if not _valid_hhmm(value):
                raise ValueError(f"{field} must be a valid HH:MM time, got {value!r}")
        return self


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
