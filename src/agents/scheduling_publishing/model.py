"""Pydantic models for Scheduling & Publishing agent."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field, PrivateAttr, validator

from .utils import parse_iso_datetime


class ContentCalendarEntry(BaseModel):
    """Content calendar entry for scheduling."""

    video_id: str = Field(..., description="รหัสวิดีโอ")
    topic_title: str = Field(..., description="ชื่อหัวข้อวิดีโอ")
    priority_score: float = Field(..., ge=0, description="คะแนนความสำคัญ")
    pillar: str = Field(..., description="เสาหลักของคอนเทนต์")
    content_type: Literal["longform", "shorts", "live", "audio"] = Field(
        ..., description="ประเภทคอนเทนต์"
    )
    expected_duration_min: int | None = Field(
        None, ge=0, description="ระยะเวลาคาดการณ์ (นาที)"
    )
    suggested_publish_week: str = Field(
        ..., pattern=r"^W\d+$", description="สัปดาห์แนะนำ (เช่น W1)"
    )
    ready_to_publish: bool = Field(..., description="สถานะความพร้อมเผยแพร่")

    @property
    def week_index(self) -> int:
        """Return numeric week index (starting at 1)."""

        return int(self.suggested_publish_week[1:])


class ScheduleConstraints(BaseModel):
    """Constraints for scheduling."""

    max_videos_per_day: int = Field(..., ge=1)
    max_longform_per_week: int = Field(..., ge=0)
    max_shorts_per_week: int = Field(..., ge=0)
    max_live_per_week: int | None = Field(
        None,
        ge=0,
        description="จำกัดจำนวน live ต่อสัปดาห์ (None หมายถึงไม่จำกัด)",
    )
    max_audio_per_week: int | None = Field(
        None,
        ge=0,
        description="จำกัดจำนวน audio ต่อสัปดาห์ (None หมายถึงไม่จำกัด)",
    )
    avoid_duplicate_pillar_in_24hr: bool = True
    forbidden_times: list[str] = Field(default_factory=list)
    planning_start_date: date | None = Field(
        None,
        description=(
            "วันเริ่มต้นสัปดาห์แรกของแผน (ตาม timezone ของ audience). หากไม่ระบุจะคำนวณอัตโนมัติ"
        ),
    )

    _forbidden_intervals_utc: list[tuple[datetime, datetime]] = PrivateAttr(
        default_factory=list
    )

    @validator("forbidden_times", each_item=True)
    def validate_forbidden_interval(cls, value: str) -> str:
        """Ensure forbidden time intervals can be parsed."""

        if "/" not in value:
            raise ValueError("forbidden time interval must use start/end format")
        start, end = value.split("/", 1)
        parse_iso_datetime(start)
        parse_iso_datetime(end)
        return value

    def __init__(self, **data: object) -> None:
        super().__init__(**data)
        self._forbidden_intervals_utc = [
            (
                parse_iso_datetime(start).astimezone(UTC),
                parse_iso_datetime(end).astimezone(UTC),
            )
            for start, end in (
                interval.split("/", 1) for interval in self.forbidden_times
            )
        ]

    @property
    def forbidden_intervals_utc(self) -> list[tuple[datetime, datetime]]:
        """Return forbidden intervals in UTC."""

        return list(self._forbidden_intervals_utc)

    def is_forbidden(self, candidate_utc: datetime) -> bool:
        """Check if the candidate datetime falls into a forbidden interval."""

        return any(
            start <= candidate_utc < end for start, end in self._forbidden_intervals_utc
        )


class AudienceAnalytics(BaseModel):
    """Analytics about audience behaviour."""

    top_time_slots_utc: list[str] = Field(..., min_items=1)
    lowest_traffic_slots_utc: list[str] = Field(default_factory=list)
    recent_best_days: list[str] = Field(..., min_items=1)
    timezone: str = Field(..., description="IANA timezone string")


class ScheduleEntry(BaseModel):
    """Single schedule entry in the plan."""

    video_id: str
    topic_title: str
    scheduled_datetime_utc: datetime | None
    scheduled_datetime_local: datetime | None
    publish_status: Literal["scheduled", "pending", "collision", "overflow"]
    pillar: str
    content_type: str
    priority_score: float
    reason: str
    collision_with: str | None = None
    overflow_reason: str | None = None
    auto_publish_ready: bool


class SelfCheck(BaseModel):
    """Self validation summary."""

    no_collision: bool
    no_overflow: bool
    all_ready_have_slot: bool


class ScheduleMeta(BaseModel):
    """Metadata summary for plan."""

    total_videos: int
    scheduled_count: int
    collision_count: int
    overflow_count: int
    pending_count: int
    pillar_distribution: dict[str, int]
    self_check: SelfCheck


class SchedulingOutput(BaseModel):
    """Output schema for scheduling agent."""

    schedule_plan: list[ScheduleEntry]
    meta: ScheduleMeta
    warnings: list[str]


class SchedulingInput(BaseModel):
    """Input schema for scheduling agent."""

    content_calendar: list[ContentCalendarEntry]
    constraints: ScheduleConstraints
    audience_analytics: AudienceAnalytics

    @validator("content_calendar")
    def validate_calendar(
        cls, value: list[ContentCalendarEntry]
    ) -> list[ContentCalendarEntry]:
        if not value:
            raise ValueError("content_calendar must not be empty")
        return value
