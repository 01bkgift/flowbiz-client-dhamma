"""
Pydantic Models สำหรับ Script Writer Agent
กำหนด Schema สำหรับ Input และ Output ของ Agent ตามข้อกำหนดใน prompt
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator

from ..research_retrieval.model import Passage
from ..script_outline.model import ScriptOutlineOutput


class SegmentType(str, Enum):
    """ประเภทของ segment ตามที่กำหนดใน prompt"""

    HOOK = "hook"
    PROBLEM = "problem"
    TRANSITION = "transition"
    STORY = "story"
    TEACHING = "teaching"
    PRACTICE = "practice"
    REFLECTION = "reflection"
    SOFT_CTA = "soft_cta"
    CLOSING = "closing"


class StyleNotes(BaseModel):
    """การตั้งค่าสไตล์การเขียนสคริปต์"""

    tone: str = Field(description="น้ำเสียงการนำเสนอ")
    voice: str = Field(description="รูปแบบการใช้ภาษา")
    avoid: list[str] = Field(description="สิ่งที่ควรหลีกเลี่ยง")


class ScriptSegment(BaseModel):
    """ส่วนหนึ่งของสคริปต์"""

    segment_type: SegmentType = Field(description="ประเภทของ segment")
    text: str = Field(description="เนื้อหาสคริปต์พร้อม citations และ retention cues")
    est_seconds: int = Field(description="เวลาประมาณการอ่าน (วินาที)", gt=0)

    @field_validator("text")
    @classmethod
    def validate_text_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("text ต้องไม่เป็นค่าว่าง")
        return v.strip()


class QualityCheck(BaseModel):
    """การตรวจสอบคุณภาพของสคริปต์"""

    citations_valid: bool = Field(description="citations ถูกต้องตาม passages")
    teaching_has_citation: bool = Field(description="ส่วน teaching มี citation")
    duration_within_range: bool = Field(description="ระยะเวลาอยู่ในช่วงเป้าหมาย")
    hook_within_8s: bool = Field(description="hook อยู่ในขีดจำกัด 8 วินาที")
    no_prohibited_claims: bool = Field(description="ไม่มีการยืนยันผลลัพธ์แน่นอน")


class ScriptMeta(BaseModel):
    """ข้อมูล metadata ของสคริปต์"""

    reading_speed_wpm: int = Field(description="ความเร็วการอ่านเฉลี่ย (คำต่อนาที)")
    interrupts_count: int = Field(description="จำนวน retention cues")
    teaching_segments: int = Field(description="จำนวน teaching segments")
    practice_steps_count: int = Field(description="จำนวนขั้นตอนใน practice")

    @field_validator("reading_speed_wpm")
    @classmethod
    def validate_reading_speed(cls, v):
        if not 100 <= v <= 200:
            raise ValueError("reading_speed_wpm ต้องอยู่ระหว่าง 100-200")
        return v


class PassageData(BaseModel):
    """โครงสร้างข้อมูล passages ที่รับจาก input"""

    primary: list[Passage] = Field(description="Passages หลัก")
    supportive: list[Passage] = Field(description="Passages สนับสนุน")


class ScriptWriterInput(BaseModel):
    """Input สำหรับ Script Writer Agent"""

    outline: ScriptOutlineOutput = Field(description="โครงร่างจาก Script Outline Agent")
    passages: PassageData = Field(description="ข้อความอ้างอิงจาก Research Retrieval Agent")
    style_notes: StyleNotes = Field(description="การตั้งค่าสไตล์")
    target_seconds: int = Field(description="เป้าหมายความยาว (วินาที)", ge=300, le=900)
    language: str = Field(default="th", description="ภาษาของสคริปต์")

    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        if v != "th":
            raise ValueError("ปัจจุบันรองรับเฉพาะภาษาไทย (th)")
        return v


class ScriptWriterOutput(BaseModel):
    """Output สำหรับ Script Writer Agent"""

    topic: str = Field(description="หัวข้อวิดีโอ")
    segments: list[ScriptSegment] = Field(description="ส่วนต่างๆ ของสคริปต์")
    citations_used: list[str] = Field(description="รายการ passage IDs ที่ใช้")
    unmatched_citations: list[str] = Field(
        default_factory=list, description="Citations ที่ไม่พบใน passages (ควรเป็นค่าว่าง)"
    )
    duration_est_total: int = Field(description="เวลารวมประมาณการ (วินาที)")
    meta: ScriptMeta = Field(description="ข้อมูล metadata")
    quality_check: QualityCheck = Field(description="การตรวจสอบคุณภาพ")
    warnings: list[str] = Field(default_factory=list, description="คำเตือนและข้อเสนอแนะ")

    @field_validator("segments")
    @classmethod
    def validate_segments_not_empty(cls, v):
        if not v:
            raise ValueError("ต้องมีอย่างน้อย 1 segment")
        return v

    @field_validator("duration_est_total")
    @classmethod
    def validate_duration_positive(cls, v):
        if v <= 0:
            raise ValueError("duration_est_total ต้องมีค่าบวก")
        return v


class ErrorResponse(BaseModel):
    """Response สำหรับกรณีเกิดข้อผิดพลาด"""

    error: dict[str, str] = Field(description="ข้อมูลข้อผิดพลาด")

    @field_validator("error")
    @classmethod
    def validate_error_structure(cls, v):
        required_keys = ["code", "message", "suggested_fix"]
        if not all(key in v for key in required_keys):
            raise ValueError(f"error ต้องมี keys: {required_keys}")
        valid_codes = ["MISSING_DATA", "SCHEMA_VIOLATION", "LOW_CONFIDENCE"]
        if v.get("code") not in valid_codes:
            raise ValueError(f"code ต้องเป็นหนึ่งใน: {valid_codes}")
        return v
