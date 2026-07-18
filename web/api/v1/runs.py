import logging

from fastapi import APIRouter, Depends, HTTPException

from web.api.dependencies import get_run_service
from web.config.exceptions import (
    NoRunsYetError,
    RunAlreadyInProgressError,
    RunOutputInvalidError,
    RunOutputMissingError,
    TrackerExecutionError,
    TrackerLaunchError,
    TrackerNotFoundError,
    TrackerTimeoutError,
)
from web.models.run_result import RunResult
from web.services.run_service import RunService

router = APIRouter(tags=["runs"])
_diag_log = logging.getLogger(__name__)


@router.post("/run", response_model=RunResult)
async def trigger_run(
    service: RunService = Depends(get_run_service),
) -> RunResult:
    _diag_log.warning("[DIAG] POST /run entered")
    print("[DIAG] POST /run entered", flush=True)
    try:
        result = await service.trigger_run()
        _diag_log.warning("[DIAG] POST /run returning result")
        print("[DIAG] POST /run returning result", flush=True)
        return result
    except RunAlreadyInProgressError:
        raise HTTPException(status_code=409, detail="A tracker run is already in progress")
    except TrackerNotFoundError:
        raise HTTPException(status_code=503, detail="Tracker script not found")
    except TrackerLaunchError as e:
        raise HTTPException(status_code=503, detail=f"Failed to launch tracker: {e.detail}")
    except TrackerTimeoutError as e:
        raise HTTPException(status_code=504, detail=f"Tracker timed out after {e.timeout_seconds}s")
    except TrackerExecutionError as e:
        raise HTTPException(status_code=502, detail=f"Tracker exited with code {e.exit_code}")
    except RunOutputMissingError:
        raise HTTPException(status_code=502, detail="Tracker produced no output")
    except RunOutputInvalidError as e:
        raise HTTPException(status_code=502, detail=f"Invalid tracker output: {e.detail}")


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
