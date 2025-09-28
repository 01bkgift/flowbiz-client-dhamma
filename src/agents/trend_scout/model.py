"""
Pydantic Models สำหรับ TrendScoutAgent
กำหนด Schema สำหรับ Input และ Output ของ Agent
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class GoogleTrendItem(BaseModel):
    """ข้อมูลเทรนด์จาก Google Trends"""

    term: str = Field(description="คำค้นหา")
    score_series: list[int] = Field(description="คะแนนเทรนด์ในแต่ละช่วงเวลา")
    region: str = Field(default="TH", description="ภูมิภาค")

    @field_validator("score_series")
    def validate_scores(cls, value: list[int]) -> list[int]:
        if not value:
            return value
        for score in value:
            if not 0 <= score <= 100:
                raise ValueError("Google Trends score ต้องอยู่ระหว่าง 0-100")
        return value


class YTTrendingItem(BaseModel):
    """ข้อมูลวิดีโอที่กำลังเทรนด์ใน YouTube"""

    title: str = Field(description="ชื่อวิดีโอ")
    views_est: int = Field(ge=0, description="จำนวนการดูโดยประมาณ")
    age_days: int = Field(ge=0, description="อายุของวิดีโอ (วัน)")
    keywords: list[str] = Field(..., min_length=1, description="คำสำคัญที่สกัดได้")


class CompetitorComment(BaseModel):
    """ความคิดเห็นจากคู่แข่ง/ช่องอื่น"""

    channel: str = Field(description="ชื่อช่อง")
    comment: str = Field(description="ความคิดเห็น")
    likes: int = Field(default=0, ge=0, description="จำนวน likes")

    @field_validator("likes")
    def validate_likes(cls, value: int) -> int:
        if value < 0:
            raise ValueError("จำนวน likes ต้องไม่เป็นลบ")
        return value


class EmbeddingSimilarGroup(BaseModel):
    """กลุ่มคำที่มีความหมายใกล้เคียง (สำหรับอนาคต)"""

    group_id: str = Field(description="ID ของกลุ่ม")
    keywords: list[str] = Field(description="คำในกลุ่ม")
    similarity_score: float = Field(ge=0, le=1, description="คะแนนความคล้าย")

    @field_validator("similarity_score")
    def validate_similarity(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("Similarity score ต้องอยู่ระหว่าง 0-1")
        return value


class TrendScoutInput(BaseModel):
    """Input สำหรับ TrendScoutAgent"""

    keywords: list[str] = Field(..., min_length=1, description="คำสำคัญที่ต้องการวิเคราะห์")
    google_trends: list[GoogleTrendItem] = Field(
        default_factory=list, description="ข้อมูลเทรนด์จาก Google"
    )
    youtube_trending_raw: list[YTTrendingItem] = Field(
        default_factory=list, description="ข้อมูลวิดีโอเทรนด์ใน YouTube"
    )
    competitor_comments: list[CompetitorComment] = Field(
        default_factory=list, description="ความคิดเห็นจากคู่แข่ง"
    )
    embeddings_similar_groups: list[EmbeddingSimilarGroup] = Field(
        default_factory=list, description="กลุ่มคำที่คล้ายกัน"
    )

    @field_validator("keywords")
    def validate_keywords(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("ต้องมีคำสำคัญอย่างน้อย 1 คำ")
        return value


class TopicScore(BaseModel):
    """คะแนนของหัวข้อในแต่ละมิติ"""

    search_intent: float = Field(ge=0, le=1, description="ความตั้งใจค้นหา")
    freshness: float = Field(ge=0, le=1, description="ความใหม่")
    evergreen: float = Field(ge=0, le=1, description="ความคงทน")
    brand_fit: float = Field(ge=0, le=1, description="ความเข้ากับแบรนด์")
    composite: float = Field(ge=0, le=1, description="คะแนนรวม")

    @field_validator(
        "search_intent", "freshness", "evergreen", "brand_fit", "composite"
    )
    def validate_score_range(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("คะแนนต้องอยู่ระหว่าง 0-1")
        return value


class TopicEntry(BaseModel):
    """หัวข้อคอนเทนต์ที่แนะนำ"""

    rank: int = Field(ge=1, description="อันดับ")
    title: str = Field(max_length=34, description="ชื่อหัวข้อ")
    pillar: str = Field(description="เสาหลักของเนื้อหา")
    predicted_14d_views: int = Field(ge=0, description="การดูคาดการณ์ 14 วัน")
    scores: TopicScore = Field(description="คะแนนในแต่ละมิติ")
    reason: str = Field(description="เหตุผลที่แนะนำ")
    raw_keywords: list[str] = Field(description="คำสำคัญต้นฉบับ")
    similar_to: list[str] = Field(default_factory=list, description="คล้ายกับหัวข้ือื่น")
    risk_flags: list[str] = Field(default_factory=list, description="ธงเตือนความเสี่ยง")

    @field_validator("rank")
    def validate_rank(cls, value: int) -> int:
        if value < 1:
            raise ValueError("อันดับต้องเป็นจำนวนเต็มบวก")
        return value

    @field_validator("predicted_14d_views")
    def validate_predicted_views(cls, value: int) -> int:
        if value < 0:
            raise ValueError("การดูคาดการณ์ต้องไม่เป็นลบ")
        return value

    @field_validator("title")
    def validate_title_length(cls, value: str) -> str:
        if len(value) > 34:
            raise ValueError("ชื่อหัวข้อยาวเกิน 34 ตัวอักษร")
        return value


class SelfCheck(BaseModel):
    """การตรวจสอบผลลัพธ์ด้วยตัวเอง"""

    duplicate_ok: bool = Field(description="ไม่มีหัวข้อซ้ำ")
    score_range_valid: bool = Field(description="คะแนนอยู่ในช่วงที่ถูกต้อง")


class MetaInfo(BaseModel):
    """ข้อมูล Meta เกี่ยวกับการประมวลผล"""

    total_candidates_considered: int = Field(description="จำนวนหัวข้อที่พิจารณาทั้งหมด")
    prediction_method: str = Field(description="วิธีการคาดการณ์")
    adjustment_notes: str = Field(default="", description="หมายเหตุการปรับแต่ง")
    self_check: SelfCheck = Field(description="การตรวจสอบผลลัพธ์")


class DiscardedDuplicate(BaseModel):
    """หัวข้อที่ถูกตัดออกเพราะซ้ำ"""

    title: str = Field(description="ชื่อหัวข้อที่ถูกตัด")
    reason: str = Field(description="เหตุผลที่ถูกตัด")


class TrendScoutOutput(BaseModel):
    """Output สำหรับ TrendScoutAgent"""

    generated_at: datetime = Field(
        default_factory=datetime.now, description="เวลาที่สร้างผลลัพธ์"
    )
    topics: list[TopicEntry] = Field(max_length=15, description="หัวข้อที่แนะนำ")
    discarded_duplicates: list[DiscardedDuplicate] = Field(
        default_factory=list, description="หัวข้อที่ถูกตัดออกเพราะซ้ำ"
    )
    meta: MetaInfo = Field(description="ข้อมูล Meta")

    @field_validator("topics")
    def validate_topics(cls, value: list["TopicEntry"]) -> list["TopicEntry"]:  # noqa: F821 (forward reference)
        if len(value) > 15:
            raise ValueError("จำนวนหัวข้อต้องไม่เกิน 15 หัวข้อ")
        if len(value) > 1:
            scores = [topic.scores.composite for topic in value]
            if scores != sorted(scores, reverse=True):
                raise ValueError("หัวข้อต้องเรียงตามคะแนน composite จากมากไปน้อย")
        return value


class ErrorResponse(BaseModel):
    """Response สำหรับกรณีเกิดข้อผิดพลาด"""

    error: bool = Field(default=True, description="เป็น error response")
    code: str = Field(description="รหัสข้อผิดพลาด")
    message: str = Field(description="ข้อความแสดงข้อผิดพลาด")
    details: dict[str, Any] | None = Field(default=None, description="รายละเอียดเพิ่มเติม")