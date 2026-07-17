import uuid

from fastapi import APIRouter, Depends, HTTPException

from web.api.dependencies import get_watchlist_service
from web.config.exceptions import WatchlistFileError, WatchlistNotFoundError
from web.models.watchlist import WatchlistEntry
from web.services.watchlist_service import WatchlistService

router = APIRouter(tags=["watchlists"])


@router.get("/watchlists", response_model=list[WatchlistEntry])
async def list_watchlists(
    service: WatchlistService = Depends(get_watchlist_service),
) -> list[WatchlistEntry]:
    try:
        return service.get_all()
    except WatchlistFileError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlists/{id}", response_model=WatchlistEntry)
async def get_watchlist(
    id: uuid.UUID,
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistEntry:
    try:
        return service.get_by_id(id)
    except WatchlistNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except WatchlistFileError as e:
        raise HTTPException(status_code=500, detail=str(e))
