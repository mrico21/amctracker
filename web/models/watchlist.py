import uuid

from pydantic import BaseModel


class WatchlistAdjacentConfig(BaseModel):
    rows: list[str]
    count: int


class WatchlistEntry(BaseModel):
    id: uuid.UUID
    index: int
    name: str
    enabled: bool
    showtime_url: str
    watch_seats: list[str]
    watch_any: list[str]
    watch_adjacent: list[WatchlistAdjacentConfig]
