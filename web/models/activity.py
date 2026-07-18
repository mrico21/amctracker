from pydantic import BaseModel


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
