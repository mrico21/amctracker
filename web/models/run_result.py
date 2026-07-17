from pydantic import BaseModel, ConfigDict, Field

from web.models.watchlist import WatchlistAdjacentConfig


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")


class WatchlistRunMonitoring(_FrozenModel):
    watch_seats: list[str] = Field(default_factory=list)
    watch_any: list[str] = Field(default_factory=list)
    watch_adjacent: list[WatchlistAdjacentConfig] = Field(default_factory=list)


class WatchlistRunResult(_FrozenModel):
    name: str
    enabled: bool
    showtime_url: str
    monitoring: WatchlistRunMonitoring
    status: str
    seats_available: int
    adjacent_windows_available: int
    notification_sent: bool
    failure_type: str | None
    error_message: str | None


class RunSummary(_FrozenModel):
    total_watchlists: int
    succeeded: int
    disabled: int
    failed: int
    notifications_sent: int
    cache_hits: int
    cache_misses: int


class FailureBreakdown(_FrozenModel):
    challenge_pages: int
    expired_urls: int
    parse_errors: int
    playwright_errors: int


class RunResult(_FrozenModel):
    schema_version: int
    generated_by: str
    generated_at: str
    run_id: str
    started_at: str
    completed_at: str
    duration_seconds: float
    tracker_version: str
    hostname: str
    run_status: str
    summary: RunSummary
    failure_breakdown: FailureBreakdown
    watchlists: list[WatchlistRunResult]
