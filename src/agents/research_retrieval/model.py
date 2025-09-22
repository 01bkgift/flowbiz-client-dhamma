"""
Pydantic Models สำหรับ Research Retrieval Agent
กำหนด Schema สำหรับ Input และ Output ของ Agent
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ResearchRetrievalInput(BaseModel):
    """Input สำหรับ Research Retrieval Agent"""

    topic_title: str = Field(description="หัวข้อหลักที่ต้องการค้นหา")
    raw_query: str = Field(description="คำค้นหาเริ่มต้น")
    refinement_hints: list[str] = Field(
        default_factory=list, description="คำแนะนำในการปรับแต่งคำค้น"
    )
    max_passages: int = Field(default=12, description="จำนวน passages สูงสุดที่ต้องการ")
    required_tags: list[str] = Field(
        default_factory=list, description="แท็กที่จำเป็นต้องมี"
    )
    forbidden_sources: list[str] = Field(
        default_factory=list, description="แหล่งที่ห้ามใช้"
    )
    context_language: str = Field(default="th", description="ภาษาของบริบท")

    @field_validator("max_passages")
    @classmethod
    def validate_max_passages(cls, v):
        if not 1 <= v <= 50:
            raise ValueError("max_passages ต้องอยู่ระหว่าง 1-50")
        return v

    @field_validator("topic_title", "raw_query")
    @classmethod
    def validate_required_text(cls, v):
        if not v or not v.strip():
            raise ValueError("ต้องระบุ topic_title และ raw_query")
        return v.strip()


class QueryUsed(BaseModel):
    """คำค้นที่ใช้ในการดึงข้อมูล"""

    type: str = Field(description="ประเภทของ query")
    query: str = Field(description="คำค้นที่ใช้")

    @field_validator("type")
    @classmethod
    def validate_query_type(cls, v):
        valid_types = ["base", "refinement_doctrine", "refinement_practice", "refinement_story"]
        if v not in valid_types:
            raise ValueError(f"ประเภท query ต้องเป็นหนึ่งใน: {valid_types}")
        return v



class Passage(BaseModel):
    """ข้อความอ้างอิงแต่ละชิ้น"""

    id: str = Field(description="รหัสประจำ passage")
    source_name: str = Field(description="ชื่อแหล่งอ้างอิง")
    collection: str = Field(description="ประเภทคลังข้อมูล")
    canonical_ref: str | None = Field(default=None, description="การอ้างอิงมาตรฐาน")
    original_text: str = Field(description="ข้อความต้นฉบับ")
    thai_modernized: str | None = Field(
        default=None, description="ข้อความที่ปรับสำนวนให้ทันสมัย"
    )
    relevance_final: float = Field(description="คะแนนความเกี่ยวข้องสุดท้าย")
    doctrinal_tags: list[str] = Field(description="แท็กหลักธรรม")
    license: str = Field(description="ข้อมูลลิขสิทธิ์")
    risk_flags: list[str] = Field(default_factory=list, description="ธงเตือนความเสี่ยง")
    reason: str = Field(description="เหตุผลที่เลือก passage นี้")
    position_score: float | None = Field(
        default=None, description="คะแนนความสำคัญในเอกสาร"
    )

    @field_validator("relevance_final")
    @classmethod
    def validate_relevance(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("relevance_final ต้องอยู่ระหว่าง 0-1")
        return v

    @field_validator("position_score")
    @classmethod
    def validate_position_score(cls, v):
        if v is not None and not 0 <= v <= 1:
            raise ValueError("position_score ต้องอยู่ระหว่าง 0-1")
        return v

    @field_validator("original_text")
    @classmethod
    def validate_original_text(cls, v):
        if not v or not v.strip():
            raise ValueError("original_text ต้องไม่เป็นค่าว่าง")
        return v


class CoverageAssessment(BaseModel):
    """การประเมินความครอบคลุมของข้อมูล"""

    core_concepts: list[str] = Field(description="แนวคิดหลักที่พบ")
    expected_concepts: list[str] = Field(description="แนวคิดที่คาดหวัง")
    missing_concepts: list[str] = Field(description="แนวคิดที่ยังขาด")
    confidence: float = Field(description="ความมั่นใจในความครอบคลุม")
    notes: str = Field(default="", description="หมายเหตุเพิ่มเติม")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("confidence ต้องอยู่ระหว่าง 0-1")
        return v


class RetrievalStats(BaseModel):
    """สถิติการดึงข้อมูล"""

    primary_count: int = Field(description="จำนวน primary passages")
    supportive_count: int = Field(description="จำนวน supportive passages")
    initial_candidates: int = Field(description="จำนวนผู้สมัครเริ่มต้น")
    filtered_out: int = Field(description="จำนวนที่ถูกกรองออก")
    avg_relevance_primary: float = Field(description="คะแนนเฉลี่ยของ primary")

    @field_validator("primary_count", "supportive_count", "initial_candidates", "filtered_out")
    @classmethod
    def validate_counts(cls, v):
        if v < 0:
            raise ValueError("จำนวนต้องไม่เป็นลบ")
        return v

    @field_validator("avg_relevance_primary")
    @classmethod
    def validate_avg_relevance(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("avg_relevance_primary ต้องอยู่ระหว่าง 0-1")
        return v


class SelfCheck(BaseModel):
    """การตรวจสอบตัวเอง"""

    has_primary: bool = Field(description="มี primary passages")
    confidence_ok: bool = Field(description="ความมั่นใจอยู่ในระดับที่ยอมรับได้")
    within_limit: bool = Field(description="จำนวน passages อยู่ในขีดจำกัด")
    no_empty_text: bool = Field(description="ไม่มีข้อความว่าง")


class MetaInfo(BaseModel):
    """ข้อมูล metadata"""

    max_passages_requested: int = Field(description="จำนวน passages ที่ขอ")
    applied_filters: list[str] = Field(description="ตัวกรองที่ใช้")
    refinement_iterations: int = Field(description="จำนวนรอบการปรับแต่ง")
    self_check: SelfCheck = Field(description="การตรวจสอบตัวเอง")


class ResearchRetrievalOutput(BaseModel):
    """Output สำหรับ Research Retrieval Agent"""

    topic: str = Field(description="หัวข้อที่ค้นหา")
    retrieved_at: datetime = Field(
        default_factory=datetime.now, description="เวลาที่ดึงข้อมูล"
    )
    queries_used: list[QueryUsed] = Field(description="คำค้นที่ใช้")
    primary: list[Passage] = Field(description="Passages หลัก")
    supportive: list[Passage] = Field(description="Passages สนับสนุน")
    summary_bullets: list[str] = Field(description="สรุปหัวใจหลัก")
    coverage_assessment: CoverageAssessment = Field(description="การประเมินความครอบคลุม")
    stats: RetrievalStats = Field(description="สถิติการดึงข้อมูล")
    meta: MetaInfo = Field(description="ข้อมูล metadata")
    warnings: list[str] = Field(default_factory=list, description="คำเตือน")

    @field_validator("summary_bullets")
    @classmethod
    def validate_summary_bullets(cls, v):
        if not 3 <= len(v) <= 6:
            raise ValueError("summary_bullets ต้องมี 3-6 ข้อ")
        return v

    @field_validator("primary", "supportive")
    @classmethod
    def validate_passages_total(cls, v, info):
        # This will be validated at the model level after both fields are set
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate total passages after model initialization"""
        total_passages = len(self.primary) + len(self.supportive)
        if total_passages > self.meta.max_passages_requested:
            raise ValueError(
                f"จำนวน passages รวม ({total_passages}) เกินที่ร้องขอ ({self.meta.max_passages_requested})"
            )


class ErrorResponse(BaseModel):
    """Response สำหรับกรณีเกิดข้อผิดพลาด"""

    error: dict[str, str] = Field(description="ข้อมูลข้อผิดพลาด")

    @field_validator("error")
    @classmethod
    def validate_error_structure(cls, v):
        required_keys = ["code", "message", "suggested_fix"]
        if not all(key in v for key in required_keys):
            raise ValueError(f"error ต้องมี keys: {required_keys}")
        return v
