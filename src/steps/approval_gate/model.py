from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class StatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED_BY_TIMEOUT = "approved_by_timeout"
    REJECTED = "rejected"


class DecisionSourceEnum(str, Enum):
    HUMAN = "human"
    TIMEOUT = "timeout"
    CONFIG = "config"
    FAILSAFE = "failsafe"


class CancelPublishAction(BaseModel):
    """Schema for output/<run_id>/control/cancel_publish.json"""

    action: Literal["cancel_publish"]
    actor: str = Field(..., min_length=1, max_length=100)
    reason: str = Field(..., min_length=1, max_length=500)


class ApprovalGateSummary(BaseModel):
    """Output schema for approval_gate_summary.json v1"""

    schema_version: Literal["v1"] = "v1"
    run_id: str = Field(..., description="Pipeline run identifier")
    opened_at_utc: str = Field(..., description="ISO8601 timestamp of first evaluation")
    resolved_at_utc: str = Field(
        ..., description="ISO8601 timestamp of latest evaluation"
    )
    status: StatusEnum = Field(..., description="Current gate status")
    decision_source: DecisionSourceEnum = Field(..., description="Source of decision")
    grace_period_minutes: int = Field(..., description="Configured grace period")
    human_action: Literal["cancel_publish"] | None = Field(
        None, description="Action taken by human"
    )
    human_actor: str | None = Field(None, description="Who took the action")
    human_reason: str | None = Field(None, description="Reason for action")
    reason_codes: list[str] = Field(
        default_factory=list, description="Machine readable reason codes"
    )
    evaluation_count: int = Field(..., description="Number of times evaluated")

    @field_validator("reason_codes")
    @classmethod
    def validate_reason_codes(cls, v):
        # Ensure we always have a list
        if v is None:
            return []
        return v
