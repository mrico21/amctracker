from typing import Literal

from pydantic import BaseModel


class JobStatus(BaseModel):
    status: Literal["idle", "starting", "running", "finished", "failed", "cancelled"] = "idle"
    run_id: str | None = None
    started_at: str | None = None
    elapsed_seconds: float = 0.0
    current_watchlist: str | None = None
    completed_watchlists: int = 0
    total_watchlists: int = 0
    error_message: str | None = None
    trigger_type: Literal["manual", "automatic", "retry", "startup"] = "manual"
