import asyncio
import json
import logging
import random
from datetime import datetime, time as dtime, timedelta, timezone

from web.config.exceptions import RunAlreadyInProgressError
from web.config.paths import ProjectPaths
from web.models.scheduler import SchedulerState, SchedulerStatus
from web.models.settings import BackendSettings
from web.services.activity_service import ActivityService
from web.services.tracker_runner import TrackerRunner

logger = logging.getLogger("amctracker.scheduler")


class SchedulerService:
    def __init__(self, paths: ProjectPaths, runner: TrackerRunner, activity: ActivityService):
        self._paths = paths
        self._runner = runner
        self._activity = activity
        self._task: asyncio.Task | None = None
        self._state: SchedulerState = self._load_state()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self, settings: BackendSettings) -> None:
        self._cancel_task()
        if settings.scheduler_enabled:
            self._task = asyncio.create_task(self._loop(settings))
            logger.info(
                "[SCHEDULER] Started - interval %ds-%ds%s",
                settings.scheduler_min_interval_seconds,
                settings.scheduler_max_interval_seconds,
                ", quiet hours enabled" if settings.scheduler_quiet_hours_enabled else "",
            )
        else:
            logger.info("[SCHEDULER] Disabled - not starting")
            self._update_state(next_run_at=None)

    def reload(self, settings: BackendSettings) -> None:
        logger.info("[SCHEDULER] Settings changed — reloading")
        self._cancel_task()
        # Clear persisted next_run_at so a fresh interval is computed
        self._update_state(next_run_at=None)
        if settings.scheduler_enabled:
            self._task = asyncio.create_task(self._loop(settings))
        else:
            logger.info("[SCHEDULER] Disabled - stopping")

    def stop(self) -> None:
        self._cancel_task()

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self, settings: BackendSettings) -> SchedulerStatus:
        state = self._state
        now = datetime.now(timezone.utc)

        countdown: float | None = None
        if state.next_run_at and settings.scheduler_enabled:
            next_dt = datetime.fromisoformat(state.next_run_at)
            remaining = (next_dt - now).total_seconds()
            countdown = max(0.0, remaining)

        if not settings.scheduler_enabled:
            status: str = "disabled"
        elif settings.scheduler_quiet_hours_enabled and self._in_quiet_hours(now, settings):
            status = "quiet"
        else:
            status = "scheduled"

        return SchedulerStatus(
            enabled=settings.scheduler_enabled,
            status=status,  # type: ignore[arg-type]
            last_triggered_at=state.last_triggered_at,
            last_trigger_type=state.last_trigger_type,
            next_run_at=state.next_run_at,
            countdown_seconds=countdown,
            min_interval_seconds=settings.scheduler_min_interval_seconds,
            max_interval_seconds=settings.scheduler_max_interval_seconds,
            quiet_hours_enabled=settings.scheduler_quiet_hours_enabled,
            quiet_hours_start=settings.scheduler_quiet_hours_start,
            quiet_hours_end=settings.scheduler_quiet_hours_end,
            randomize_order=settings.scheduler_randomize_order,
        )

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def _loop(self, settings: BackendSettings) -> None:
        try:
            await self._scheduler_loop(settings)
        except asyncio.CancelledError:
            logger.info("[SCHEDULER] Task cancelled")
        except Exception as e:
            logger.exception("[SCHEDULER] Unexpected error: %s", e)

    async def _scheduler_loop(self, settings: BackendSettings) -> None:
        now = datetime.now(timezone.utc)

        # Honour persisted next_run_at if it's still in the future
        sleep_seconds: float
        if self._state.next_run_at:
            next_dt = datetime.fromisoformat(self._state.next_run_at)
            remaining = (next_dt - now).total_seconds()
            sleep_seconds = remaining if remaining > 5 else self._random_interval(settings)
        else:
            sleep_seconds = self._random_interval(settings)

        while True:
            next_dt = datetime.now(timezone.utc) + timedelta(seconds=sleep_seconds)
            self._update_state(next_run_at=next_dt.isoformat())
            logger.info(
                "[SCHEDULER] Next run in %.0fs (at %s UTC)",
                sleep_seconds,
                next_dt.strftime("%H:%M:%S"),
            )

            await asyncio.sleep(sleep_seconds)

            now = datetime.now(timezone.utc)

            # Quiet hours check
            if settings.scheduler_quiet_hours_enabled and self._in_quiet_hours(now, settings):
                wake_at = self._quiet_hours_end_dt(now, settings)
                wait = max(30.0, (wake_at - now).total_seconds())
                logger.info(
                    "[SCHEDULER] Quiet hours active — sleeping until %s local",
                    wake_at.astimezone().strftime("%H:%M"),
                )
                self._update_state(next_run_at=wake_at.isoformat())
                await asyncio.sleep(wait)
                sleep_seconds = self._random_interval(settings)
                continue

            # No-overlap guard
            if self._runner.is_running:
                logger.info("[SCHEDULER] Skipping - run already in progress")
                self._activity.make_and_append(
                    event_type="scheduler_skipped",
                    message="Scheduler skipped - run already in progress",
                    payload={},
                )
                sleep_seconds = self._random_interval(settings)
                continue

            # Fire
            now_iso = datetime.now(timezone.utc).isoformat()
            self._update_state(
                last_triggered_at=now_iso,
                last_trigger_type="automatic",
                next_run_at=None,
            )
            logger.info("[SCHEDULER] Triggering automatic run")
            self._activity.make_and_append(
                event_type="scheduler_triggered",
                message="Scheduler triggered automatic run",
                payload={"triggered_at": now_iso},
            )
            try:
                await self._runner.launch_background(settings, trigger_type="automatic")
            except RunAlreadyInProgressError:
                logger.info("[SCHEDULER] Race condition - run already started")
            except Exception as e:
                logger.error("[SCHEDULER] Failed to launch run: %s", e)

            sleep_seconds = self._random_interval(settings)

    # ── Quiet hours helpers ───────────────────────────────────────────────────

    def _in_quiet_hours(self, dt: datetime, settings: BackendSettings) -> bool:
        local_time = dt.astimezone().time().replace(second=0, microsecond=0)
        start = dtime.fromisoformat(settings.scheduler_quiet_hours_start)
        end = dtime.fromisoformat(settings.scheduler_quiet_hours_end)
        if start <= end:
            return start <= local_time < end
        # Spans midnight
        return local_time >= start or local_time < end

    def _quiet_hours_end_dt(self, now: datetime, settings: BackendSettings) -> datetime:
        local_now = now.astimezone()
        end = dtime.fromisoformat(settings.scheduler_quiet_hours_end)
        candidate = local_now.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
        if candidate <= local_now:
            candidate += timedelta(days=1)
        return candidate.astimezone(timezone.utc)

    # ── Interval helper ───────────────────────────────────────────────────────

    def _random_interval(self, settings: BackendSettings) -> float:
        lo = float(settings.scheduler_min_interval_seconds)
        hi = float(settings.scheduler_max_interval_seconds)
        if lo >= hi:
            return lo
        return random.uniform(lo, hi)

    # ── State persistence ─────────────────────────────────────────────────────

    def _load_state(self) -> SchedulerState:
        path = self._paths.scheduler_state_file
        if not path.is_file():
            return SchedulerState()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return SchedulerState.model_validate(data)
        except Exception as e:
            logger.warning("[SCHEDULER] Could not load scheduler_state.json: %s", e)
            return SchedulerState()

    def _update_state(self, **kwargs) -> None:
        self._state = self._state.model_copy(update=kwargs)
        self._persist_state()

    def _persist_state(self) -> None:
        path = self._paths.scheduler_state_file
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(self._state.model_dump_json(indent=2), encoding="utf-8")
            tmp.replace(path)
        except Exception as e:
            logger.warning("[SCHEDULER] Failed to persist state: %s", e)

    def _cancel_task(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
