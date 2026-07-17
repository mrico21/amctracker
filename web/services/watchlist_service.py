import json
import uuid

from web.config.exceptions import WatchlistFileError, WatchlistNotFoundError
from web.config.paths import ProjectPaths
from web.models.watchlist import WatchlistAdjacentConfig, WatchlistEntry


class WatchlistService:
    def __init__(self, paths: ProjectPaths):
        self._paths = paths

    def get_all(self) -> list[WatchlistEntry]:
        data = self._load_raw()
        return [
            self._parse_entry(raw, index=i + 1)
            for i, raw in enumerate(data.get("watchlists", []))
        ]

    def get_by_id(self, id: uuid.UUID) -> WatchlistEntry:
        data = self._load_raw()
        for i, raw in enumerate(data.get("watchlists", [])):
            try:
                if uuid.UUID(raw["id"]) == id:
                    return self._parse_entry(raw, index=i + 1)
            except (KeyError, ValueError):
                continue
        raise WatchlistNotFoundError(id=id)

    def _load_raw(self) -> dict:
        wf = self._paths.watchlist_file
        try:
            return json.loads(wf.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise WatchlistFileError(f"watchlist.json not found: {wf}")
        except json.JSONDecodeError as e:
            raise WatchlistFileError(f"watchlist.json is not valid JSON: {e}")
        except Exception as e:
            raise WatchlistFileError(f"Could not read watchlist.json: {e}")

    @staticmethod
    def _normalize_entry(raw: dict) -> dict:
        return {
            **raw,
            "enabled": raw["enabled"] if "enabled" in raw else True,
            "watch_seats": raw.get("watch_seats", []),
            "watch_any": raw.get("watch_any", []),
            "watch_adjacent": raw.get("watch_adjacent", []),
        }

    def _parse_entry(self, raw: dict, index: int) -> WatchlistEntry:
        normalized = self._normalize_entry(raw)
        try:
            return WatchlistEntry(
                id=uuid.UUID(normalized["id"]),
                index=index,
                name=normalized["name"],
                enabled=normalized["enabled"],
                showtime_url=normalized["showtime_url"],
                watch_seats=normalized["watch_seats"],
                watch_any=normalized["watch_any"],
                watch_adjacent=[
                    WatchlistAdjacentConfig(**adj)
                    for adj in normalized["watch_adjacent"]
                ],
            )
        except (KeyError, ValueError) as e:
            raise WatchlistFileError(f"Invalid watchlist entry at position {index}: {e}")
