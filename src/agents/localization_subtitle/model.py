"""Pydantic models for the localization subtitle agent."""

from __future__ import annotations

import math
import re
from typing import ClassVar

from pydantic import BaseModel, Field, field_validator, model_validator

TIMESTAMP_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}$")


def parse_timestamp_to_seconds(timestamp: str) -> float:
    """Convert SRT timestamp to total seconds."""
    if not TIMESTAMP_PATTERN.match(timestamp):
        raise ValueError("timestamp ไม่อยู่ในรูปแบบ HH:MM:SS,mmm")

    hours = int(timestamp[0:2])
    minutes = int(timestamp[3:5])
    seconds = int(timestamp[6:8])
    milliseconds = int(timestamp[9:12])

    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0


def format_seconds_to_timestamp(value: float) -> str:
    """Format seconds to SRT timestamp."""
    total_milliseconds = int(round(value * 1000))
    hours, remainder = divmod(total_milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


class SubtitleSegment(BaseModel):
    """A single subtitle segment from the approved script."""

    segment_type: str = Field(description="ประเภทของ segment")
    text: str = Field(description="ข้อความจากสคริปต์ที่อนุมัติแล้ว")
    est_seconds: float = Field(gt=0, description="ระยะเวลาโดยประมาณ (วินาที)")

    @field_validator("segment_type", "text")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("ค่านี้ต้องไม่เป็นค่าว่าง")
        return value.strip()

    @field_validator("est_seconds")
    @classmethod
    def validate_duration(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("est_seconds ต้องมากกว่า 0")
        return float(value)


class LocalizationSubtitleInput(BaseModel):
    """Input payload for the localization subtitle agent."""

    approved_script: list[SubtitleSegment] = Field(
        min_length=1, description="รายการสคริปต์ที่ได้รับการอนุมัติ"
    )
    base_start_time: str = Field(
        description="เวลาเริ่มต้นสำหรับบล็อกแรก (รูปแบบ HH:MM:SS,mmm)"
    )

    @field_validator("base_start_time")
    @classmethod
    def validate_base_start_time(cls, value: str) -> str:
        value = value.strip()
        if not TIMESTAMP_PATTERN.match(value):
            raise ValueError("base_start_time ต้องอยู่ในรูปแบบ HH:MM:SS,mmm")
        return value


class LocalizationSubtitleMeta(BaseModel):
    """Metadata calculated for the generated subtitle."""

    lines: int = Field(ge=1, description="จำนวนบรรทัดทั้งหมดในไฟล์ SRT")
    duration_total: float = Field(ge=0, description="ระยะเวลารวมตั้งแต่เริ่มจนจบบล็อกสุดท้าย")
    segments_count: int = Field(ge=1, description="จำนวนบล็อก subtitle")
    time_continuity_ok: bool = Field(description="เวลาของแต่ละบล็อกต่อเนื่องกันโดยไม่มีช่องว่าง")
    no_overlap: bool = Field(description="ไม่มีการซ้อนทับของเวลา")
    no_empty_line: bool = Field(description="ไม่มีบรรทัดข้อความว่างในแต่ละบล็อก")
    self_check: bool = Field(
        description="ตรวจสอบตนเองผ่านทุกข้อ (continuity, overlap, empty line)"
    )

    @field_validator("lines", "segments_count")
    @classmethod
    def validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("ต้องมีค่ามากกว่า 0")
        return value

    @field_validator("duration_total")
    @classmethod
    def validate_duration_total(cls, value: float) -> float:
        if value < 0:
            raise ValueError("duration_total ต้องไม่ติดลบ")
        return float(value)


class LocalizationSubtitleOutput(BaseModel):
    """Output payload from the localization subtitle agent."""

    srt: str = Field(description="เนื้อหาไฟล์ SRT แบบครบถ้วน")
    english_summary: str = Field(description="สรุปภาษาอังกฤษ 50-100 คำ")
    meta: LocalizationSubtitleMeta = Field(description="ข้อมูล metadata")
    warnings: list[str] = Field(default_factory=list, description="รายการคำเตือน")

    @field_validator("srt")
    @classmethod
    def validate_srt_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("srt ต้องไม่เป็นค่าว่าง")
        return value.strip()

    @field_validator("english_summary")
    @classmethod
    def validate_summary_length(cls, value: str) -> str:
        words = [w for w in re.split(r"\s+", value.strip()) if w]
        if not 50 <= len(words) <= 100:
            raise ValueError("english_summary ต้องมีความยาว 50-100 คำ")
        return " ".join(words)

    @model_validator(mode="after")
    def validate_structure(self) -> LocalizationSubtitleOutput:
        blocks = [
            block.strip()
            for block in re.split(r"\n\s*\n", self.srt.strip())
            if block.strip()
        ]
        if not blocks:
            raise ValueError("srt ต้องมีอย่างน้อย 1 block")

        timestamp_line_pattern = re.compile(
            r"^(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2},\d{3})$"
        )

        calculated_lines = 0
        calculated_duration = 0.0
        continuity_ok = True
        no_overlap = True
        no_empty = True
        first_start = None
        last_end = None

        for index, block in enumerate(blocks, start=1):
            raw_lines = block.splitlines()
            lines = [line.rstrip() for line in raw_lines]
            calculated_lines += len(raw_lines)

            if not lines:
                raise ValueError("แต่ละบล็อกต้องมีเนื้อหา")

            if lines[0].strip() != str(index):
                raise ValueError("หมายเลขบล็อก srt ต้องเรียงต่อเนื่อง")

            if len(lines) < 2:
                raise ValueError("บล็อกต้องมีบรรทัดเวลา")

            timestamp_line = lines[1].strip()
            match = timestamp_line_pattern.match(timestamp_line)
            if not match:
                raise ValueError("timestamp ต้องอยู่ในรูปแบบ SRT มาตรฐาน")

            start_seconds = parse_timestamp_to_seconds(match.group("start"))
            end_seconds = parse_timestamp_to_seconds(match.group("end"))
            if start_seconds >= end_seconds:
                raise ValueError("เวลาเริ่มต้องน้อยกว่าเวลาสิ้นสุด")

            if first_start is None:
                first_start = start_seconds

            if last_end is not None:
                if not math.isclose(
                    start_seconds, last_end, rel_tol=1e-4, abs_tol=1e-3
                ):
                    continuity_ok = False
                if start_seconds < last_end - 1e-3:
                    no_overlap = False

            text_section = lines[2:]
            if not text_section:
                raise ValueError("ต้องมีข้อความ subtitle ในแต่ละบล็อก")

            if any(not row.strip() for row in text_section):
                no_empty = False

            last_end = end_seconds

        if first_start is None or last_end is None:
            raise ValueError("ข้อมูลเวลาไม่ครบถ้วน")

        calculated_duration = last_end - first_start

        if len(blocks) != self.meta.segments_count:
            raise ValueError("meta.segments_count ต้องตรงกับจำนวนบล็อกใน srt")

        if calculated_lines != self.meta.lines:
            raise ValueError("meta.lines ต้องตรงกับจำนวนบรรทัดที่นับได้")

        if not math.isclose(
            calculated_duration, self.meta.duration_total, rel_tol=1e-4, abs_tol=1e-3
        ):
            raise ValueError("meta.duration_total ไม่ตรงกับข้อมูลใน srt")

        if self.meta.time_continuity_ok != continuity_ok:
            raise ValueError("meta.time_continuity_ok ไม่ตรงกับข้อมูลจริง")

        if self.meta.no_overlap != no_overlap:
            raise ValueError("meta.no_overlap ไม่ตรงกับข้อมูลจริง")

        if self.meta.no_empty_line != no_empty:
            raise ValueError("meta.no_empty_line ไม่ตรงกับข้อมูลจริง")

        expected_self_check = continuity_ok and no_overlap and no_empty
        if self.meta.self_check != expected_self_check:
            raise ValueError("meta.self_check ต้องเป็น True เมื่อผ่านทุกการตรวจสอบ")

        return self
