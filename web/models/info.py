from pydantic import BaseModel


class InfoResponse(BaseModel):
    api_version: str
    schema_version: int
    hostname: str
    run_in_progress: bool
    tracker_version: str | None
    last_run_id: str | None
    last_run_status: str | None
    last_run_at: str | None
    commit_hash: str | None
    server_started_at: str
