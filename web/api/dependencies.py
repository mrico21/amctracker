from functools import lru_cache

from fastapi import Depends

from web.config.paths import ProjectPaths
from web.models.settings import BackendSettings
from web.services.health_service import HealthService
from web.services.history_service import HistoryService
from web.services.info_service import InfoService
from web.services.run_service import RunService
from web.services.settings_service import SettingsService
from web.services.tracker_runner import TrackerRunner
from web.services.watchlist_service import WatchlistService


@lru_cache()
def get_project_paths() -> ProjectPaths:
    return ProjectPaths()


def get_settings(
    paths: ProjectPaths = Depends(get_project_paths),
) -> BackendSettings:
    return SettingsService(paths).load()


def get_health_service(
    paths: ProjectPaths = Depends(get_project_paths),
    settings: BackendSettings = Depends(get_settings),
) -> HealthService:
    return HealthService(paths, settings)


def get_info_service(
    paths: ProjectPaths = Depends(get_project_paths),
) -> InfoService:
    return InfoService(paths)


def get_settings_service(
    paths: ProjectPaths = Depends(get_project_paths),
) -> SettingsService:
    return SettingsService(paths)


def get_watchlist_service(
    paths: ProjectPaths = Depends(get_project_paths),
) -> WatchlistService:
    return WatchlistService(paths)


@lru_cache()
def get_tracker_runner() -> TrackerRunner:
    return TrackerRunner(get_project_paths())


def get_is_running(
    runner: TrackerRunner = Depends(get_tracker_runner),
) -> bool:
    return runner.is_running


def get_run_service(
    paths: ProjectPaths = Depends(get_project_paths),
    settings: BackendSettings = Depends(get_settings),
    runner: TrackerRunner = Depends(get_tracker_runner),
) -> RunService:
    return RunService(paths, settings, runner)


def get_history_service(
    paths: ProjectPaths = Depends(get_project_paths),
    settings: BackendSettings = Depends(get_settings),
) -> HistoryService:
    return HistoryService(paths, settings)
