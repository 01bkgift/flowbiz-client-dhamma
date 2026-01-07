from typing import Literal

from pydantic import BaseModel, Field


class NotifyTarget(BaseModel):
    name: str
    url: str


class TargetResult(BaseModel):
    name: str
    url_redacted: str
    result: Literal["success", "error", "timeout"]
    http_status: int | None = None


class NotifySummary(BaseModel):
    schema_version: str = "v1"
    run_id: str
    timestamp_utc: str
    notification_status: Literal["sent", "failed", "skipped"]
    targets_attempted: list[TargetResult] = Field(default_factory=list)
    message_digest: str
    reason_codes: list[str] = Field(default_factory=list)
