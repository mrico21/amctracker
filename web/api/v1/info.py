from fastapi import APIRouter, Depends

from web.api.dependencies import get_info_service, get_is_running
from web.models.info import InfoResponse
from web.services.info_service import InfoService

router = APIRouter(tags=["system"])


@router.get("/info", response_model=InfoResponse)
async def get_info(
    service: InfoService = Depends(get_info_service),
    is_running: bool = Depends(get_is_running),
) -> InfoResponse:
    return service.get_info(is_running)
