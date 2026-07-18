from fastapi import APIRouter, Depends

from web.api.dependencies import get_settings_service
from web.models.settings import SettingsResponse, SettingsUpdate
from web.services.settings_service import SettingsService

router = APIRouter(tags=["configuration"])


@router.get("/settings", response_model=SettingsResponse)
async def get_settings_config(
    service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    return service.get_response()


@router.put("/settings", response_model=SettingsResponse)
async def put_settings_config(
    body: SettingsUpdate,
    service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    service.update(body)
    return service.get_response()
