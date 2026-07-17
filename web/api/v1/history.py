import uuid

from fastapi import APIRouter, Depends, HTTPException

from web.api.dependencies import get_history_service
from web.config.exceptions import HistoryRunNotFoundError, RunOutputInvalidError
from web.models.history import HistoryResponse
from web.models.run_result import RunResult
from web.services.history_service import HistoryService

router = APIRouter(tags=["history"])


@router.get("/history", response_model=HistoryResponse)
async def list_history(
    service: HistoryService = Depends(get_history_service),
) -> HistoryResponse:
    return service.get_all()


@router.get("/history/{run_id}", response_model=RunResult)
async def get_history_run(
    run_id: uuid.UUID,
    service: HistoryService = Depends(get_history_service),
) -> RunResult:
    try:
        return service.get_by_id(run_id)
    except HistoryRunNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    except RunOutputInvalidError as e:
        raise HTTPException(status_code=500, detail=f"Archived run is corrupt: {e.detail}")
