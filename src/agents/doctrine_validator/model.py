"""Pydantic models สำหรับ DoctrineValidatorAgent"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SegmentStatus(StrEnum):
    """สถานะการตรวจสอบของแต่ละ segment"""

    OK = "ok"
    UNCLEAR = "unclear"
    MISMATCH = "mismatch"
    HALLUCINATION = "hallucination"
    MISSING_CITATION = "missing_citation"
    UNVERIFIABLE = "unverifiable"


class SegmentType(StrEnum):
    """ประเภทของ segment"""

    TEACHING = "teaching"
    HOOK = "hook"
    STORY = "story"
    PRACTICE = "practice"
    REFLECTION = "reflection"
    TRANSITION = "transition"
    PROBLEM = "problem"
    SOFT_CTA = "soft_cta"
    CLOSING = "closing"
    OTHER = "other"

    @classmethod
    def from_raw(cls, value: str) -> SegmentType:
        """สร้าง SegmentType จาก string แบบยืดหยุ่น"""

        normalized = (value or "").strip().lower()
        for member in cls:
            if normalized == member.value:
                return member
        return cls.OTHER


class ScriptSegment(BaseModel):
    """ข้อมูลสคริปต์แต่ละส่วน"""

    segment_type: str = Field(description="ประเภท segment จากสคริปต์")
    text: str = Field(description="ข้อความของ segment")
    est_seconds: int | None = Field(default=None, description="เวลาประมาณ")

    @property
    def normalized_type(self) -> SegmentType:
        return SegmentType.from_raw(self.segment_type)


class Passage(BaseModel):
    """ข้อมูลข้อความอ้างอิง"""

    id: str = Field(description="รหัสอ้างอิง")
    original_text: str = Field(description="ข้อความต้นฉบับ")
    thai_modernized: str | None = Field(default=None, description="คำแปลไทยร่วมสมัย")
    doctrinal_tags: list[str] = Field(default_factory=list, description="แท็กหลักธรรม")
    canonical_ref: str | None = Field(default=None, description="เลขอ้างอิงในพระไตรปิฎก")
    license: str | None = Field(default=None, description="สถานะลิขสิทธิ์")


class Passages(BaseModel):
    """ชุดข้อความอ้างอิงหลักและเสริม"""

    primary: list[Passage] = Field(default_factory=list, description="primary passages")
    supportive: list[Passage] = Field(
        default_factory=list, description="supportive passages"
    )

    @field_validator("primary", "supportive")
    @classmethod
    def ensure_ids(cls, values: list[Passage]):
        ids = {p.id for p in values}
        if len(ids) != len(values):
            raise ValueError("passage id ต้องไม่ซ้ำกันในแต่ละรายการ")
        return values


class DoctrineValidatorInput(BaseModel):
    """Input สำหรับ DoctrineValidatorAgent"""

    script_segments: list[ScriptSegment] = Field(description="รายการ segment ของสคริปต์")
    passages: Passages = Field(description="ข้อความอ้างอิง")
    strictness: Literal["normal", "strict"] = Field(
        default="normal", description="ระดับความเข้มงวด"
    )
    ignore_segments: list[int] = Field(
        default_factory=list, description="ดัชนี segment ที่ข้ามการตรวจ"
    )
    check_sensitive: bool = Field(default=False, description="ตรวจคำที่สุ่มเสี่ยงหรือไม่")

    @field_validator("script_segments")
    @classmethod
    def validate_segments(cls, value: list[ScriptSegment]):
        if not value:
            raise ValueError("ต้องมี script_segments อย่างน้อย 1 รายการ")
        return value


class SegmentValidation(BaseModel):
    """ผลการตรวจสอบราย segment"""

    index: int
    segment_type: str
    text: str
    status: SegmentStatus
    matched_passages: list[str]
    notes: str | None = None
    warnings: list[str] = Field(default_factory=list)
    suggestions: str | None = None


class Summary(BaseModel):
    """สรุปผลรวม"""

    total: int
    ok: int
    mismatch: int
    hallucination: int
    unclear: int
    missing_citation: int
    unverifiable: int
    recommend_rewrite: bool


class RewriteSuggestion(BaseModel):
    """คำแนะนำการปรับปรุง"""

    segment_index: int
    suggestion: str


class SelfCheck(BaseModel):
    """ผลการตรวจสอบด้วยตัวเอง"""

    ok_ratio: float
    no_unmatched_citation: bool
    no_missing_citation: bool


class MetaInfo(BaseModel):
    """ข้อมูลเพิ่มเติมของผลการตรวจ"""

    citation_coverage: float
    overall_confidence: float
    strictness: str
    self_check: SelfCheck


class DoctrineValidatorOutput(BaseModel):
    """Output หลักของ DoctrineValidatorAgent"""

    validated_at: str
    strictness: str
    segments: list[SegmentValidation]
    summary: Summary
    rewrite_suggestions: list[RewriteSuggestion]
    meta: MetaInfo
    warnings: list[str]


class ErrorResponse(BaseModel):
    """รูปแบบการตอบกลับเมื่อเกิดข้อผิดพลาด"""

    error: dict[str, str]
