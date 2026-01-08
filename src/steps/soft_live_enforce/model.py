from typing import Literal

from pydantic import BaseModel, Field


class SoftLiveSummary(BaseModel):
    schema_version: Literal["v1"] = "v1"
    run_id: str
    timestamp_utc: str
    soft_live_status: Literal["enabled", "disabled", "failed"]
    enforced_mode: Literal["dry_run", "unlisted", "private"] | None = None
    reason_codes: list[str] = Field(default_factory=list)
