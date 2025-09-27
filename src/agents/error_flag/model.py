"""Pydantic models for the Error/Flag agent."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class AgentError(BaseModel):
    """รายละเอียด error จาก agent อื่น."""

    code: str = Field(..., description="รหัส error จาก agent")
    message: str = Field(..., description="ข้อความอธิบาย error")
    suggested_fix: str | None = Field(
        default=None,
        description="คำแนะนำการแก้ไขจาก agent ต้นทาง",
        alias="suggested_fix",
    )


class AgentLog(BaseModel):
    """ข้อมูล log ต่อ agent ที่ Error/Flag agent ใช้เป็น input."""

    agent: str = Field(..., description="ชื่อ agent ที่ส่ง log")
    error: AgentError | None = Field(default=None, description="ข้อมูล error ถ้ามี")
    flags: list[str] = Field(default_factory=list, description="รายการ flag")
    warnings: list[str] = Field(
        default_factory=list, description="รายการ warning จาก agent"
    )


class ErrorFlagInput(BaseModel):
    """Input schema สำหรับ ErrorFlagAgent."""

    agent_logs: list[AgentLog] = Field(
        default_factory=list, description="ลิสต์ log จาก agent ทั้งหมด"
    )


class CriticalItem(BaseModel):
    """โครงสร้างข้อมูลสำหรับ Critical severity."""

    agent: str
    error_code: str
    message: str
    suggested_action: str | None = None


class WarningItem(BaseModel):
    """โครงสร้างข้อมูลสำหรับ Warning severity."""

    agent: str
    flag: str | None = None
    warning: str | None = None
    message: str
    suggested_action: str | None = None

    @model_validator(mode="after")
    def _ensure_flag_or_warning(self) -> WarningItem:
        if not self.flag and not self.warning:
            raise ValueError("ต้องมี flag หรือ warning อย่างน้อยหนึ่งตัว")
        return self


class SelfCheck(BaseModel):
    """ผลการ self-check ของ agent."""

    all_sections_present: bool
    no_empty_fields: bool


class MetaSection(BaseModel):
    """ข้อมูลสรุปเชิงสถิติของ ErrorFlagAgent."""

    total_error: int
    total_flag: int
    total_warning: int
    unique_agents: int
    self_check: SelfCheck


class ErrorFlagOutput(BaseModel):
    """Output schema ตามที่ workflow ต้องการ."""

    summary: list[str]
    critical: list[CriticalItem]
    warning: list[WarningItem]
    info: list[str]
    root_cause: list[str]
    meta: MetaSection


__all__ = [
    "AgentError",
    "AgentLog",
    "ErrorFlagInput",
    "ErrorFlagOutput",
    "CriticalItem",
    "WarningItem",
    "MetaSection",
    "SelfCheck",
]
