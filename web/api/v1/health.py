from fastapi import APIRouter, Depends

from web.api.dependencies import get_health_service
from web.models.health import HealthResponse
from web.services.health_service import HealthService

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def get_health(
    service: HealthService = Depends(get_health_service),
) -> HealthResponse:
    return service.check()
