from fastapi import APIRouter, Depends

from web.api.dependencies import get_scheduler_service, get_settings
from web.models.scheduler import SchedulerStatus
from web.models.settings import BackendSettings
from web.services.scheduler_service import SchedulerService

router = APIRouter(tags=["scheduler"])


@router.get("/scheduler/status", response_model=SchedulerStatus)
async def get_scheduler_status(
    service: SchedulerService = Depends(get_scheduler_service),
    settings: BackendSettings = Depends(get_settings),
) -> SchedulerStatus:
    return service.get_status(settings)
