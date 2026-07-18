from typing import Literal

from pydantic import BaseModel


class SchedulerState(BaseModel):
    last_triggered_at: str | None = None
    last_trigger_type: str | None = None
    next_run_at: str | None = None


class SchedulerStatus(BaseModel):
    enabled: bool
    status: Literal["disabled", "scheduled", "quiet"]
    last_triggered_at: str | None
    last_trigger_type: str | None
    next_run_at: str | None
    countdown_seconds: float | None
    min_interval_seconds: int
    max_interval_seconds: int
    quiet_hours_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str
    randomize_order: bool
