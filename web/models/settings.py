import sys

from pydantic import BaseModel, model_validator


class BackendSettings(BaseModel):
    run_timeout_seconds: int = 300
    max_history_runs: int = 50
    python_executable: str = ""
    cors_origins: list[str] = ["*"]

    @model_validator(mode="after")
    def fill_python_default(self) -> "BackendSettings":
        if not self.python_executable:
            self.python_executable = "py" if sys.platform == "win32" else "python3"
        return self


class SettingsUpdate(BaseModel):
    run_timeout_seconds: int
    max_history_runs: int
    python_executable: str
    cors_origins: list[str]


class SettingsResponse(BaseModel):
    run_timeout_seconds: int
    max_history_runs: int
    python_executable: str
    cors_origins: list[str]
    tracker_script: str
    watchlist_file: str
