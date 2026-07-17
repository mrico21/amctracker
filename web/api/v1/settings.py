from fastapi import APIRouter, Depends

from web.api.dependencies import get_settings_service
from web.models.settings import SettingsResponse
from web.services.settings_service import SettingsService

router = APIRouter(tags=["configuration"])


@router.get("/settings", response_model=SettingsResponse)
async def get_settings_config(
    service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    return service.get_response()
