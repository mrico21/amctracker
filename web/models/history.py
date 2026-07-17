import uuid

from pydantic import BaseModel

from web.models.run_result import RunResult


class RunHistorySummary(BaseModel):
    run_id: uuid.UUID
    completed_at: str
    run_status: str
    duration_seconds: float
    tracker_version: str
    notifications_sent: int
    total_watchlists: int
    succeeded: int
    failed: int

    @classmethod
    def from_run_result(cls, r: RunResult) -> "RunHistorySummary":
        return cls(
            run_id=uuid.UUID(r.run_id),
            completed_at=r.completed_at,
            run_status=r.run_status,
            duration_seconds=r.duration_seconds,
            tracker_version=r.tracker_version,
            notifications_sent=r.summary.notifications_sent,
            total_watchlists=r.summary.total_watchlists,
            succeeded=r.summary.succeeded,
            failed=r.summary.failed,
        )


class HistoryResponse(BaseModel):
    runs: list[RunHistorySummary]
    skipped_files: list[str]
