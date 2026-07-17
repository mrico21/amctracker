import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from web.api.dependencies import get_project_paths
from web.api.v1 import router as v1_router
from web.services.settings_service import SettingsService
from web.startup.watchlist_migration import ensure_watchlist_ids

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("amctracker.api")

# Read settings at import time to configure CORS before lifespan.
# get_project_paths() is lru_cached — same instance reused by all DI calls.
_paths = get_project_paths()
_startup_settings = SettingsService(_paths).load()


@asynccontextmanager
async def lifespan(app: FastAPI):
    paths = get_project_paths()
    paths.runs_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    logger.info("AMCTracker API starting")
    ensure_watchlist_ids(paths)
    logger.info(f"  tracker_root={paths.project_root}")
    logger.info(f"  python_executable={_startup_settings.python_executable}")
    logger.info(f"  run_timeout_seconds={_startup_settings.run_timeout_seconds}")
    logger.info(f"  cors_origins={_startup_settings.cors_origins}")
    yield
    logger.info("AMCTracker API shutting down")


app = FastAPI(
    title="AMCTracker API",
    version="1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_startup_settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")

# Serve the React frontend from dist/ when it exists (production / after `npm run build`).
# In development, the Vite dev server handles the frontend and proxies /api to FastAPI.
if _paths.frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=_paths.frontend_dist, html=True), name="frontend")
