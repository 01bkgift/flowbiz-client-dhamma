from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DecisionEnum(str, Enum):
    RECOMMEND_PUBLISH = "recommend_publish"
    RECOMMEND_HOLD = "recommend_hold"
    RECOMMEND_EDIT = "recommend_edit"


class DecisionSupportOutput(BaseModel):
    """Output schema for decision_support_summary.json v1"""

    schema_version: str = Field(default="v1", description="Schema version")
    generated_at: str = Field(..., description="ISO8601 timestamp")
    run_id: str = Field(..., description="Pipeline run identifier")
    decision: DecisionEnum = Field(..., description="The recommended action")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score 0.0-1.0"
    )
    reasons: list[str] = Field(..., description="List of stable reason codes")
    recommendations: list[str] = Field(
        ..., description="Human-readable recommendations"
    )
    inputs_used: dict[str, str] = Field(
        ..., description="Map of artifact key to path used"
    )
    notes: str | None = Field(None, description="Optional operator notes")
