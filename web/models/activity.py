from typing import Literal

from pydantic import BaseModel

# Canonical set of event types emitted by the tracker and scheduler.
# Must stay in sync with ActivityEventType in web/frontend/src/api/types.ts.
ActivityEventType = Literal[
    "run_start",
    "watchlist_start",
    "watchlist_complete",
    "watchlist_blocked",
    "watchlist_failed",
    "watchlist_expiry_warning",
    "watchlist_expired",
    "watchlist_expiry_recovered",
    "notification_sent",
    "notification_failed",
    "run_complete",
    "run_cancelled",
    "scheduler_triggered",
    "scheduler_skipped",
]


class ActivityEvent(BaseModel):
    id: str
    timestamp: str
    event_type: str
    message: str
    payload: dict
    run_id: str | None = None


class EventsResponse(BaseModel):
    events: list[ActivityEvent]
    total: int
