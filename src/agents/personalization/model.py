"""Pydantic models for PersonalizationAgent"""

from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserProfile(BaseModel):
    """ข้อมูลโปรไฟล์ผู้ใช้"""

    model_config = ConfigDict(extra="forbid")

    age: int | None = Field(default=None, ge=0, description="อายุของผู้ใช้")
    gender: str | None = Field(default=None, description="เพศ")
    location: str | None = Field(default=None, description="ที่อยู่")
    interest: list[str] = Field(
        default_factory=list, description="รายการความสนใจหลักของผู้ใช้"
    )

    @field_validator("interest", mode="before")
    @classmethod
    def normalize_interest(cls, value: list[str] | None) -> list[str]:
        if not value:
            return []
        return [
            cleaned_item for item in value if item and (cleaned_item := item.strip())
        ]


class ViewHistoryItem(BaseModel):
    """ประวัติการรับชมของผู้ใช้"""

    model_config = ConfigDict(extra="forbid")

    video_id: str = Field(description="รหัสวิดีโอ")
    title: str = Field(description="ชื่อวิดีโอ")
    watched_pct: float = Field(ge=0, le=100, description="เปอร์เซ็นต์ที่รับชม")
    date: dt_date = Field(description="วันที่รับชม")

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, value: dt_date | str) -> dt_date:
        if isinstance(value, dt_date):
            return value
        try:
            return datetime.fromisoformat(value).date()
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError("รูปแบบวันที่ไม่ถูกต้อง (ต้องเป็น YYYY-MM-DD)") from exc


class EngagementMetrics(BaseModel):
    """ข้อมูล engagement ล่าสุดของผู้ใช้"""

    model_config = ConfigDict(extra="forbid")

    like: int = Field(default=0, ge=0, description="จำนวนถูกใจ")
    comment: int = Field(default=0, ge=0, description="จำนวนคอมเมนต์")
    share: int = Field(default=0, ge=0, description="จำนวนการแชร์")

    @property
    def total(self) -> int:
        """รวมทุก engagement"""

        return self.like + self.comment + self.share


class TrendInterest(BaseModel):
    """คะแนนความนิยมของหัวข้อในช่วงปัจจุบัน"""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(description="ชื่อหัวข้อ")
    score: float = Field(ge=0, le=100, description="คะแนนความนิยม")


class PersonalizationConfig(BaseModel):
    """การตั้งค่าการแนะนำส่วนบุคคล"""

    model_config = ConfigDict(extra="forbid")

    recommend_top_n: int = Field(default=3, ge=1, le=10, description="จำนวนคำแนะนำ")
    min_confidence_pct: int = Field(
        default=70, ge=0, le=100, description="ค่าความมั่นใจขั้นต่ำ"
    )


class PersonalizationRequest(BaseModel):
    """ข้อมูลคำขอสำหรับการทำ personalization"""

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(description="รหัสผู้ใช้")
    profile: UserProfile = Field(default_factory=UserProfile)
    view_history: list[ViewHistoryItem] = Field(
        default_factory=list, description="ประวัติการรับชม"
    )
    engagement: EngagementMetrics = Field(
        default_factory=EngagementMetrics, description="ข้อมูล engagement"
    )
    trend: list[TrendInterest] = Field(
        default_factory=list, description="ข้อมูลเทรนด์ปัจจุบัน"
    )
    config: PersonalizationConfig = Field(
        default_factory=PersonalizationConfig, description="การตั้งค่าการแนะนำ"
    )


class PersonalizationInput(BaseModel):
    """รูปแบบ input สำหรับ PersonalizationAgent"""

    model_config = ConfigDict(extra="forbid")

    personalization_request: PersonalizationRequest


class RecommendationItem(BaseModel):
    """คำแนะนำแต่ละรายการ"""

    model_config = ConfigDict(extra="forbid")

    type: Literal["video", "topic", "feature"]
    reason: str = Field(description="เหตุผลที่แนะนำ")
    confidence_pct: int = Field(ge=0, le=100, description="ความมั่นใจ (%)")
    priority: int = Field(ge=1, description="ลำดับความสำคัญ")
    video_id: str | None = Field(default=None, description="รหัสวิดีโอ")
    title: str | None = Field(default=None, description="ชื่อวิดีโอ")
    topic: str | None = Field(default=None, description="หัวข้อคอนเทนต์")
    feature: str | None = Field(default=None, description="ฟีเจอร์หรือแคมเปญ")

    @model_validator(mode="after")
    def validate_required_fields(self) -> RecommendationItem:
        match self.type:
            case "video":
                if not self.video_id or not self.title:
                    raise ValueError("video recommendation ต้องมี video_id และ title")
            case "topic":
                if not self.topic:
                    raise ValueError("topic recommendation ต้องมี topic")
            case "feature":
                if not self.feature:
                    raise ValueError("feature recommendation ต้องมี feature")
        if not self.reason.strip():
            raise ValueError("reason ต้องไม่ว่าง")
        return self


class PersonalizationSelfCheck(BaseModel):
    """ผลการตรวจสอบตัวเองของระบบแนะนำ"""

    model_config = ConfigDict(extra="forbid")

    all_sections_present: bool = Field(description="มีทุก section ที่จำเป็น")
    no_empty_fields: bool = Field(description="ไม่มีฟิลด์ที่ว่างโดยไม่จำเป็น")


class PersonalizationMeta(BaseModel):
    """ข้อมูล meta เพิ่มเติมของผลลัพธ์"""

    model_config = ConfigDict(extra="forbid")

    recommend_top_n: int = Field(description="จำนวนคำแนะนำที่ต้องการ")
    min_confidence_pct: int = Field(description="ค่าความมั่นใจขั้นต่ำ")
    self_check: PersonalizationSelfCheck


class PersonalizedRecommendation(BaseModel):
    """คำแนะนำต่อผู้ใช้รายบุคคล"""

    model_config = ConfigDict(extra="forbid")

    recommend_to: str = Field(description="รหัสผู้ใช้ที่แนะนำให้")
    recommendation: list[RecommendationItem] = Field(
        description="รายการคำแนะนำที่เรียงตามลำดับความสำคัญ"
    )
    action_plan: list[str] = Field(default_factory=list, description="แผนปฏิบัติ")
    alert: list[str] = Field(default_factory=list, description="คำเตือนหรือสัญญาณที่พบ")
    meta: PersonalizationMeta

    @model_validator(mode="after")
    def ensure_priorities_sorted(self) -> PersonalizedRecommendation:
        priorities = [item.priority for item in self.recommendation]
        if priorities != sorted(priorities):
            raise ValueError("priority ต้องเรียงจากน้อยไปมาก")
        return self


class PersonalizationOutput(BaseModel):
    """ผลลัพธ์จาก PersonalizationAgent"""

    model_config = ConfigDict(extra="forbid")

    personalized_recommendation: list[PersonalizedRecommendation]
