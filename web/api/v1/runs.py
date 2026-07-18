from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from web.api.dependencies import get_run_service
from web.config.exceptions import (
    NoRunsYetError,
    RunAlreadyInProgressError,
    RunOutputInvalidError,
)
from web.models.job_status import JobStatus
from web.models.run_result import RunResult
from web.services.run_service import RunService

router = APIRouter(tags=["runs"])


@router.post("/run", status_code=202)
async def trigger_run(
    service: RunService = Depends(get_run_service),
) -> JSONResponse:
    try:
        await service.launch_background()
    except RunAlreadyInProgressError:
        raise HTTPException(status_code=409, detail="A tracker run is already in progress")
    return JSONResponse(
        status_code=202,
        content={"status": "starting", "message": "Tracker run started"},
    )


@router.post("/run/cancel")
async def cancel_run(
    service: RunService = Depends(get_run_service),
) -> dict:
    if not service.cancel():
        raise HTTPException(status_code=409, detail="No run is currently in progress")
    return {"status": "cancelled"}


@router.get("/run/status", response_model=JobStatus)
async def get_run_status(
    service: RunService = Depends(get_run_service),
) -> JobStatus:
    return service.job_status


@router.get("/run/latest", response_model=RunResult)
async def get_latest_run(
    service: RunService = Depends(get_run_service),
) -> RunResult:
    try:
        return service.get_latest()
    except NoRunsYetError:
        raise HTTPException(status_code=404, detail="No runs have completed yet")
    except RunOutputInvalidError as e:
        raise HTTPException(status_code=500, detail=f"latest.json is corrupt: {e.detail}")
