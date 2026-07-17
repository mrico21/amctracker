import json
import logging
import uuid

from web.config.paths import ProjectPaths

logger = logging.getLogger("amctracker.api")

WATCHLIST_FORMAT_VERSION = 1


def ensure_watchlist_ids(paths: ProjectPaths) -> None:
    """Assign a stable UUID to any watchlist entry that lacks one. Idempotent."""
    wf = paths.watchlist_file
    if not wf.is_file():
        logger.warning("ensure_watchlist_ids: watchlist.json not found, skipping")
        return

    try:
        data = json.loads(wf.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"ensure_watchlist_ids: could not read watchlist.json: {e}")
        return

    entries = data.get("watchlists", [])
    seen_ids: set[str] = set()
    modified = 0

    for entry in entries:
        raw_id = entry.get("id")
        existing_id: str | None = None

        if raw_id:
            try:
                existing_id = str(uuid.UUID(str(raw_id)))
            except ValueError:
                pass

        if existing_id is None or existing_id in seen_ids:
            existing_id = str(uuid.uuid4())
            entry["id"] = existing_id
            modified += 1

        seen_ids.add(existing_id)

    if modified == 0:
        logger.info(f"watchlist IDs already initialized ({len(entries)} entries)")
        return

    tmp = wf.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(wf)
        logger.info(
            f"watchlist migration completed (assigned IDs to {modified} of {len(entries)} entries)"
        )
    except Exception as e:
        logger.error(f"ensure_watchlist_ids: failed to write watchlist.json: {e}")
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
