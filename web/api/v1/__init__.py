from fastapi import APIRouter

from web.api.v1 import events, health, history, info, runs, scheduler, settings, watchlists

router = APIRouter()
router.include_router(events.router)
router.include_router(health.router)
router.include_router(history.router)
router.include_router(info.router)
router.include_router(runs.router)
router.include_router(scheduler.router)
router.include_router(settings.router)
router.include_router(watchlists.router)
