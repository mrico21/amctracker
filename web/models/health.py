from typing import Literal

from pydantic import BaseModel


class HealthCheckResult(BaseModel):
    status: Literal["ok", "error"]
    detail: str | None


class HealthResponse(BaseModel):
    status: Literal["healthy", "unhealthy"]
    checks: dict[str, HealthCheckResult]
