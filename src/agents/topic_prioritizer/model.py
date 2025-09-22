"""
Pydantic Models สำหรับ TopicPrioritizerAgent v1
กำหนด Schema สำหรับการสร้าง Content Calendar จากหัวข้อที่แนะนำ
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Import TopicEntry from trend_scout
from ..trend_scout.model import TopicEntry


class CandidateTopic(BaseModel):
    """หัวข้อผู้สมัครสำหรับการจัดลำดับ"""

    title: str = Field(description="ชื่อหัวข้อ")
    pillar: str = Field(description="เสาหลักของเนื้อหา")
    predicted_14d_views: int = Field(description="การดูคาดการณ์ 14 วัน")
    scores: dict[str, float] = Field(description="คะแนนในแต่ละมิติ")
    reason: str = Field(description="เหตุผลที่แนะนำ")


class WeeksCapacity(BaseModel):
    """ข้อมูลความจุต่อสัปดาห์"""

    weeks: int = Field(description="จำนวนสัปดาห์", default=4)
    longform_per_week: int = Field(description="จำนวน longform ต่อสัปดาห์")
    shorts_per_week: int = Field(description="จำนวน shorts ต่อสัปดาห์")


class Rules(BaseModel):
    """กฎการจัดสรรเนื้อหา"""

    min_pillars_diversity: int = Field(description="จำนวน pillar ขั้นต่ำ", default=3)
    force_series_prefixes: list[str] = Field(
        description="คำขึ้นต้นที่บังคับให้เป็นซีรีส์",
        default_factory=lambda: ["พุทธจิตวิทยา", "ชาดกชุด", "10 วันภาวนา"],
    )


class HistoricalContext(BaseModel):
    """ข้อมูลประวัติศาสตร์ช่อง"""

    recent_longform_avg_views: int = Field(description="ยอดวิว longform เฉลี่ยล่าสุด")
    recent_shorts_avg_views: int = Field(description="ยอดวิว shorts เฉลี่ยล่าสุด")
    pillar_performance: dict[str, float] = Field(
        description="ผลการดำเนินงานของแต่ละ pillar", default_factory=dict
    )


class PriorityInput(BaseModel):
    """Input สำหรับ TopicPrioritizerAgent v1"""

    candidate_topics: list[CandidateTopic] = Field(
        description="หัวข้อผู้สมัครจาก TrendScout"
    )
    strategy_focus: Literal["fast_growth", "evergreen_balance", "depth_series"] = Field(
        description="กลยุทธ์หลักที่เน้น"
    )
    capacity: WeeksCapacity = Field(description="ความจุการผลิต")
    rules: Rules | None = Field(default_factory=Rules, description="กฎการจัดสรร")
    historical_context: HistoricalContext | None = Field(
        default=None, description="ข้อมูลประวัติศาสตร์"
    )

    @field_validator("candidate_topics")
    @classmethod
    def validate_topics(cls, v):
        if not v:
            raise ValueError("ต้องมีหัวข้อผู้สมัครอย่างน้อย 1 หัวข้อ")
        return v


class ScheduledTopic(BaseModel):
    """หัวข้อที่ถูกจัดในปฏิทิน"""

    topic_title: str = Field(description="ชื่อหัวข้อ")
    content_type: Literal["longform", "shorts"] = Field(description="ประเภทเนื้อหา")
    pillar: str = Field(description="เสาหลักของเนื้อหา")
    week: str = Field(description="สัปดาห์ (W1-W4)")
    slot_index: int = Field(description="ลำดับในสัปดาห์")
    priority_score: float = Field(description="คะแนนความสำคัญ")
    expected_role: Literal[
        "traffic_spike",
        "evergreen_seed",
        "series_part",
        "balance_filler",
        "audience_engagement",
    ] = Field(description="บทบาทที่คาดหวัง")
    series_group: str | None = Field(default=None, description="กลุ่มซีรีส์")
    risk_flags: list[str] = Field(default_factory=list, description="ธงเตือนความเสี่ยง")
    notes: str = Field(description="หมายเหตุ")

    @field_validator("priority_score")
    @classmethod
    def validate_priority_score(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("คะแนนความสำคัญต้องอยู่ระหว่าง 0-100")
        return v


class UnscheduledTopic(BaseModel):
    """หัวข้อที่ไม่ได้ถูกจัดในปฏิทิน"""

    topic_title: str = Field(description="ชื่อหัวข้อ")
    reason: Literal["capacity_full", "low_score", "pillar_overrepresented"] = Field(
        description="เหตุผลที่ไม่ได้จัดในปฏิทิน"
    )
    priority_score: float = Field(description="คะแนนความสำคัญ")


class DiversitySummary(BaseModel):
    """สรุปความหลากหลายของ pillar"""

    pillar_counts: dict[str, int] = Field(description="จำนวนหัวข้อของแต่ละ pillar")
    distinct_pillars: int = Field(description="จำนวน pillar ที่แตกต่าง")
    meets_minimum: bool = Field(description="เป็นไปตามเกณฑ์ขั้นต่ำหรือไม่")


class SelfCheck(BaseModel):
    """การตรวจสอบผลลัพธ์ด้วยตัวเอง"""

    capacity_respected: bool = Field(description="เคารพข้อจำกัดความจุ")
    scores_monotonic: bool = Field(description="คะแนนเรียงลำดับถูกต้อง")
    diversity_ok: bool = Field(description="ความหลากหลายเป็นไปตามเกณฑ์")


class MetaInfo(BaseModel):
    """ข้อมูล Meta เกี่ยวกับการประมวลผล"""

    total_candidates: int = Field(description="จำนวนหัวข้อผู้สมัครทั้งหมด")
    scheduled_count: int = Field(description="จำนวนหัวข้อที่จัดในปฏิทิน")
    unscheduled_count: int = Field(description="จำนวนหัวข้อที่ไม่ได้จัดในปฏิทิน")
    pillars_underrepresented: list[str] = Field(
        default_factory=list, description="Pillar ที่มีสัดส่วนน้อย"
    )
    adjustments_notes: str = Field(description="หมายเหตุการปรับแต่ง")
    self_check: SelfCheck = Field(description="ผลการตรวจสอบด้วยตัวเอง")


class PriorityOutput(BaseModel):
    """Output สำหรับ TopicPrioritizerAgent v1"""

    plan_generated_at: str = Field(description="เวลาที่สร้างแผน (ISO8601)")
    strategy_focus: str = Field(description="กลยุทธ์ที่ใช้")
    weeks_capacity: dict[str, int] = Field(description="ความจุต่อสัปดาห์")
    scheduled: list[ScheduledTopic] = Field(description="หัวข้อที่จัดในปฏิทิน")
    unscheduled: list[UnscheduledTopic] = Field(description="หัวข้อที่ไม่ได้จัดในปฏิทิน")
    diversity_summary: DiversitySummary = Field(description="สรุปความหลากหลาย")
    meta: MetaInfo = Field(description="ข้อมูล Meta")


class ErrorResponse(BaseModel):
    """Response สำหรับกรณีเกิดข้อผิดพลาด"""

    error: dict[str, str] = Field(description="ข้อมูลข้อผิดพลาด")


# Legacy models for backward compatibility
class PriorityScore(BaseModel):
    """คะแนนความสำคัญในแต่ละมิติ (Legacy)"""

    roi_potential: float = Field(description="ศักยภาพ ROI (0-100)")
    risk_level: float = Field(description="ระดับความเสี่ยง (0-100)")
    brand_alignment: float = Field(description="ความสอดคล้องกับแบรนด์ (0-100)")
    production_difficulty: float = Field(description="ความยากในการผลิต (0-100)")
    priority_score: float = Field(description="คะแนนความสำคัญรวม (0-100)")

    @field_validator(
        "roi_potential",
        "risk_level",
        "brand_alignment",
        "production_difficulty",
        "priority_score",
    )
    @classmethod
    def validate_score_range(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("คะแนนต้องอยู่ระหว่าง 0-100")
        return v


class PrioritizedTopic(BaseModel):
    """หัวข้อที่ได้รับการจัดลำดับความสำคัญแล้ว (Legacy)"""

    original_topic: TopicEntry = Field(description="หัวข้อต้นฉบับ")
    priority_rank: int = Field(description="อันดับความสำคัญ")
    priority_scores: PriorityScore = Field(description="คะแนนความสำคัญ")
    business_justification: str = Field(description="เหตุผลเชิงธุรกิจ")
    production_notes: str = Field(description="หมายเหตุการผลิต")

    @field_validator("priority_rank")
    @classmethod
    def validate_priority_rank(cls, v):
        if v < 1:
            raise ValueError("อันดับความสำคัญต้องเป็นจำนวนเต็มบวก")
        return v
