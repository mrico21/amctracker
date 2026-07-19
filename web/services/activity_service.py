import json
import logging
import threading
import uuid
from collections import deque
from datetime import datetime, timezone

from web.config.paths import ProjectPaths
from web.models.activity import ActivityEvent

logger = logging.getLogger("amctracker.activity")

_MAX_EVENTS = 500


class ActivityService:
    def __init__(self, paths: ProjectPaths):
        self._paths = paths
        self._lock = threading.Lock()
        self._events: deque[ActivityEvent] = deque(self._load(), maxlen=_MAX_EVENTS)

    # ── Public API ────────────────────────────────────────────────────────────

    def append(self, event: ActivityEvent) -> None:
        with self._lock:
            self._events.append(event)
            self._persist()

    def make_and_append(
        self,
        event_type: str,
        message: str,
        payload: dict,
        run_id: str | None = None,
    ) -> ActivityEvent:
        event = ActivityEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            message=message,
            payload=payload,
            run_id=run_id,
        )
        self.append(event)
        return event

    def get_events(self) -> list[ActivityEvent]:
        with self._lock:
            return list(reversed(self._events))

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> list[ActivityEvent]:
        path = self._paths.activity_file
        if not path.is_file():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            events = [ActivityEvent.model_validate(e) for e in raw]
            return events[-_MAX_EVENTS:]
        except Exception as e:
            logger.warning("Could not load activity.json: %s", e)
            return []

    def _persist(self) -> None:
        path = self._paths.activity_file
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            data = [e.model_dump() for e in self._events]
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(path)
        except Exception as e:
            logger.warning("Failed to persist activity.json: %s", e)
