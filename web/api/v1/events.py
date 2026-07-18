from fastapi import APIRouter, Depends

from web.api.dependencies import get_activity_service
from web.models.activity import EventsResponse
from web.services.activity_service import ActivityService

router = APIRouter(tags=["events"])


@router.get("/events", response_model=EventsResponse)
async def get_events(
    service: ActivityService = Depends(get_activity_service),
) -> EventsResponse:
    events = service.get_events()
    return EventsResponse(events=events, total=len(events))
